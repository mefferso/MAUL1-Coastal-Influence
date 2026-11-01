import datetime as dt
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import archive_monitoring as monitoring


UTC = dt.timezone.utc


def stamp(hour, minute=0, day=1):
    return dt.datetime(2026, 11, day, tzinfo=UTC)+dt.timedelta(hours=hour, minutes=minute)


def receipt(station, variable, when, retrieved=None, value=1.0, parameter="", datum="not_applicable"):
    return {"station_id":station, "variable":variable, "parameter_code":parameter, "datum":datum,
            "record_type":"observation", "valid_time":when.isoformat().replace("+00:00", "Z"),
            "retrieved_at":(retrieved or when).isoformat().replace("+00:00", "Z"), "value":value,
            "unit":"ft","status":"provisional", "qc_flags":[], "acquisition_mode":"prospective"}


class TestArchiveMonitoring(unittest.TestCase):
    def test_context_keeps_provider_status_labels_without_upgrading_them(self):
        issue=stamp(1)
        provisional=receipt("DENL1","stream_stage",stamp(0),stamp(0,5),value=2.0)
        provisional["status"]="provisional"
        approved_revision={**provisional,"status":"approved","retrieved_at":stamp(0,10).isoformat().replace("+00:00","Z")}
        result=monitoring.assess_context([provisional,approved_revision],"DENL1",["stream_stage"],issue)
        self.assertEqual(result["features"][0]["provider_status_counts"],{"approved":1,"provisional":1})
        self.assertEqual(result["features"][0]["unique_valid_times"],1)
        self.assertTrue(result["features"][0]["cadence_provisional"])

    def test_schedule_report_distinguishes_recorded_runs_from_nominal_slots(self):
        now=stamp(12)
        runs=[
            {"event":"schedule", "created_at":stamp(0,43).isoformat(), "run_started_at":stamp(0,45).isoformat(), "status":"completed", "conclusion":"success"},
            {"event":"schedule", "created_at":stamp(5,43).isoformat(), "run_started_at":stamp(5,43).isoformat(), "status":"completed", "conclusion":"failure"},
            {"event":"schedule", "created_at":stamp(6,43).isoformat(), "status":"completed", "conclusion":"cancelled"},
            {"event":"schedule", "created_at":stamp(8,43).isoformat(), "status":"completed", "conclusion":"startup_failure"},
            {"event":"pull_request", "created_at":stamp(7,43).isoformat(), "status":"completed", "conclusion":"success"},
        ]
        report=monitoring.build_schedule_report(runs, now, lookback_hours=24)
        self.assertEqual(report["expected_hourly_slots"], 24)
        self.assertEqual(report["actual_scheduled_runs"], 4)
        self.assertEqual(report["conclusions"]["success"], 1)
        self.assertEqual(report["conclusions"]["failure"], 2)
        self.assertEqual(report["conclusions"]["cancelled"], 1)
        self.assertEqual(report["conclusions"]["skipped"], 0)
        self.assertEqual(report["nominal_slots_without_run_record"], 20)
        self.assertEqual(report["raw_conclusions"]["startup_failure"],1)
        self.assertEqual(report["non_schedule_runs_excluded"], 1)

    def test_actions_history_client_follows_pages(self):
        class Response:
            def __init__(self,payload): self.payload=payload
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self): return json.dumps(self.payload).encode()
        page1={"total_count":101,"workflow_runs":[{"id":i,"event":"schedule"} for i in range(100)]}
        page2={"total_count":101,"workflow_runs":[{"id":100,"event":"schedule"}]}
        requests=[]
        def opener(request,timeout=30):
            requests.append(request)
            page=monitoring.urllib.parse.parse_qs(monitoring.urllib.parse.urlparse(request.full_url).query)["page"][0]
            return Response(page1 if page=="1" else page2)
        with patch.object(monitoring.urllib.request,"urlopen",side_effect=opener):
            runs=monitoring.fetch_scheduled_runs("mefferso/MAUL1-Coastal-Influence","token",stamp(12))
        self.assertEqual(len(runs),101)
        self.assertEqual(len(requests),2)
        self.assertIn("actions/workflows/forcing-archive.yml/runs",requests[0].full_url)
        self.assertEqual(requests[0].get_header("Authorization"),"Bearer token")

    def test_late_recovery_counts_eventually_but_not_at_earlier_issue(self):
        issue=stamp(3)
        rows=[receipt("NWCL1","wind_u",stamp(h), stamp(h) if h==0 else stamp(6,5), value=float(h)) for h in range(7)]
        for row in rows[1:]:
            row["acquisition_mode"]="delayed_recovery"
        before=monitoring.available_rows_at_issue(rows, issue)
        after=monitoring.available_rows_at_issue(rows, stamp(7))
        self.assertEqual(len(before), 1)
        self.assertEqual(len(after), 7)
        self.assertEqual(sum(row["acquisition_mode"]=="delayed_recovery" for row in after),6)
        self.assertTrue(all(monitoring.parse_time(r["retrieved_at"]) > monitoring.parse_time(r["valid_time"])
                            for r in after if monitoring.parse_time(r["valid_time"]) > stamp(0)))

    def test_wind_window_fails_on_large_gap_and_invalid_vector_pair(self):
        issue=stamp(12)
        rows=[]
        for hour in [0,6,7,12]:
            value=None if hour==7 else 4.0
            u=receipt("NWCL1","wind_u",stamp(hour),value=value)
            if hour==6:
                u["qc_flags"]=["invalid provider value"]
            rows.extend([u,receipt("NWCL1","wind_v",stamp(hour),value=2.0)])
        result=monitoring.assess_window(rows,"NWCL1",("wind_u","wind_v"),issue,6,cadence_seconds=3600)
        self.assertFalse(result["ready"])
        self.assertGreater(result["max_gap_seconds"], 3*3600)
        self.assertGreater(result["invalid_vector_times"], 0)
        self.assertEqual(result["interpolated_points"], 0)

    def test_absent_rainfall_or_tributary_is_reported_missing(self):
        result=monitoring.assess_context([], "MAUL1", ["rainfall","gage_height"], stamp(12), 24)
        self.assertEqual(result["status"], "missing")
        self.assertEqual(result["available_variables"], [])

    def test_maul1_navd88_context_uses_direct_63160_only(self):
        issue=stamp(12)
        native=receipt("MAUL1","water_level",stamp(11),parameter="00065",datum="native_gage_datum:USGS-07380215")
        direct=receipt("MAUL1","water_level",stamp(11),parameter="63160",datum="NAVD88",value=1.8)
        result=monitoring.assess_context([native,direct],"MAUL1",["water_level"],issue,24,"63160","NAVD88")
        self.assertEqual(result["features"][0]["datum"],"NAVD88")
        self.assertEqual(result["features"][0]["parameter_code"],"63160")
        self.assertEqual(result["features"][0]["unique_valid_times"],1)

    def test_overlapping_significant_rise_windows_merge_into_one_episode(self):
        rows=[]
        for hour in range(49):
            value=0.0 if hour < 24 else 0.5
            rows.append(receipt("MAUL1","gage_height",stamp(hour), value=value,
                                parameter="00065", datum="native_gage_datum:USGS-07380215"))
        episodes=monitoring.significant_rise_episodes(rows,cadence_seconds=3600)
        self.assertEqual(len(episodes),1)
        self.assertGreaterEqual(episodes[0]["rise_ft"],0.5)
        self.assertGreater(episodes[0]["overlapping_windows_merged"],1)

    def test_insufficient_independent_events_are_not_called_validation_ready(self):
        report=monitoring.assess_validation_readiness(matured_targets={6:4,12:3,24:1},
            rise_episodes=[], forcing_periods=0, provisional_minimum_independent_rises=3)
        self.assertEqual(report["status"],"Insufficient independent events")
        self.assertFalse(report["model_validated"])
        self.assertEqual(report["provisional_review_threshold_independent_rises"],3)

    def test_recovery_requires_successful_scheduled_run_and_receipt_acquired_during_it(self):
        run={"event":"schedule","created_at":"2026-11-01T00:43:00Z","run_started_at":"2026-11-01T00:43:02Z",
             "updated_at":"2026-11-01T00:44:00Z","conclusion":"success","head_sha":monitoring.RECOVERY_MERGE_SHA,
             "html_url":"https://example.test/run"}
        row=receipt("NWCL1","water_level",stamp(0),stamp(0,43,day=1)+dt.timedelta(seconds=5),value=1.2)
        row["acquisition_mode"]="delayed_recovery"
        report=monitoring._recovery_deployment_report(pathlib.Path("."),[row],[run],monitoring.RECOVERY_MERGED_AT)
        self.assertTrue(report["production_recovery_observed"])
        self.assertEqual(report["delayed_recovery_receipts_acquired_after_merge"],1)
        self.assertFalse(monitoring._recovery_deployment_report(pathlib.Path("."),[row],[],monitoring.RECOVERY_MERGED_AT)["production_recovery_observed"])

    def test_matured_forecast_targets_deduplicate_model_rows_and_revisions(self):
        record={"issuance_id":"i1","horizon_hours":24,"forecast_valid_time_utc":"2026-11-01T12:00:00Z",
                "observation_valid_time_utc":"2026-11-01T12:30:00Z","observation_ingested_utc":"2026-11-02T00:00:00Z"}
        counts=monitoring._matured_targets([{**record,"model":"persistence"},{**record,"model":"phase5b","revision":2},
            {**record,"issuance_id":"i2","horizon_hours":6}])
        self.assertEqual(counts,{6:1,12:0,24:1})
        self.assertEqual(monitoring._matured_targets([record],as_of=stamp(0)),{6:0,12:0,24:0})

    def test_significant_rise_requires_a_prospective_verification_target(self):
        events=[{"start_valid_time":"2026-11-01T00:00:00Z","end_valid_time":"2026-11-02T00:00:00Z","rise_ft":0.6}]
        unmatched=monitoring.match_verified_events(events,[])
        matched=monitoring.match_verified_events(events,[{"observation_valid_time_utc":"2026-11-01T18:00:00Z",
            "observation_ingested_utc":"2026-11-02T06:00:00Z","observed_native_stage_ft":2.0}])
        self.assertEqual(unmatched,[])
        self.assertEqual(len(matched),1)
        self.assertEqual(matched[0]["prospective_verification_targets"],1)

    def test_reports_write_idempotently_for_same_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=pathlib.Path(tmp)/"report.json"
            data={"as_of":"2026-11-01", "assessment":{"status":"insufficient evidence"}}
            first=monitoring.write_json_if_changed(path,data)
            contents=path.read_bytes()
            second=monitoring.write_json_if_changed(path,data)
            self.assertTrue(first)
            self.assertFalse(second)
            self.assertEqual(path.read_bytes(),contents)
            markdown=path.with_suffix(".md")
            self.assertTrue(monitoring.write_text_if_changed(markdown,"stable summary\n"))
            self.assertFalse(monitoring.write_text_if_changed(markdown,"stable summary\n"))


if __name__ == "__main__":
    unittest.main()
