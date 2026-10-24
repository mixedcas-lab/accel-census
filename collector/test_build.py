"""Offline tests: python3 -m unittest discover -s collector -v"""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402
import classify as C  # noqa: E402


class TestRelevance(unittest.TestCase):
    def test_core(self):
        for t in ("CIMFormer: A 38.9TOPS/W-8b Systolic CIM-Array Based Transformer Processor with Token-Slimmed Attention",
                  "A 28-nm 18.7 TOPS/mm² 89.4-to-234.6 TOPS/W 8b Single-Finger eDRAM Compute-in-Memory Macro",
                  "HWSA: A High-Ratio Weight Sparse Accelerator for Efficient CNN Inference",
                  "A Multi-Mode 8k-MAC HW-Utilization-Aware Neural Processing Unit With a Unified Multi-Precision Datapath",
                  "SamurAI: A Versatile IoT Node With Event-Driven Wake-Up and Embedded ML Acceleration",
                  "A Heterogeneous RRAM In-Memory and SRAM Near-Memory SoC for Fused Frame and Event-Based Target Tracking",
                  "Hardware-Software Co-Design for Vector Similarity Search on HBM-PIM"):
            self.assertEqual(C.relevance(t, ""), "core", t)

    def test_rf_and_power_transformers_are_not_ml(self):
        for t in ("A Transformer-Based Quadrature Doherty Digital Power Amplifier With 4.1 W Peak Power in 28 nm Bulk CMOS",
                  "A 52–73-GHz LNA With Tri-Coupled Transformer for Gm Boosting",
                  "A 63% Efficiency 1.29-W Isolated DC–DC Converter Using FPC Micro-Transformer"):
            self.assertIsNone(C.relevance(t, ""), t)

    def test_neural_recording_and_ml_for_eda_are_out(self):
        self.assertIsNone(C.relevance("A 1024-Channel Data-Compressive Neural Recording IC for Brain–Computer Interfaces", ""))
        self.assertIsNone(C.relevance("Machine Learning-Based Routing Congestion Prediction for FPGA Placement", ""))

    def test_generic_words_are_not_enough(self):
        for t in ("TICA: Timing Slack Inference and Clock Frequency Adaption Technique for a Deeply Pipelined Near-Threshold Processor",
                  "A 0.18-µg Bias-Instability Silicon Oscillating Accelerometer"):
            self.assertIsNone(C.relevance(t, ""), t)
        self.assertEqual(C.relevance("A 28nm 1.07TFLOPS/mm2 Dynamic-Precision Training Processor", ""), "core")

    def test_abstract_only(self):
        self.assertEqual(C.relevance("A Mobile Application Processor in 4 nm",
                                     "The SoC integrates an NPU for on-device inference."), "related")


class TestSpecs(unittest.TestCase):
    def test_title(self):
        s = C.parse_specs("A 28-nm 18.7 TOPS/mm² 89.4-to-234.6 TOPS/W 8b Single-Finger eDRAM Compute-in-Memory Macro", "")
        self.assertEqual((s["eff"], s["aeff"], s["node"], s["prec"]), (234.6, 18.7, 28, 8))

    def test_gops_per_mw_and_tflops(self):
        s = C.parse_specs("SP-PIM: A 22.41TFLOPS/W Super-Pipelined Processing-In-Memory Accelerator", "")
        self.assertAlmostEqual(s["eff"], 22.41)
        s = C.parse_specs("An accelerator", "It achieves 3.1 GOPS/mW and a peak throughput of 820 GOPS at 200 MHz, consuming 45 mW.")
        self.assertAlmostEqual(s["eff"], 3.1)
        self.assertAlmostEqual(s["thr"], 0.82)
        self.assertEqual((s["f"], s["p"]), (200e6, 0.045))

    def test_energy_per_mac(self):
        s = C.parse_specs("A CIM macro", "The macro consumes 10 fJ/MAC.")
        self.assertAlmostEqual(s["eff"], 200.0)

    def test_memory_and_precision(self):
        s = C.parse_specs("A 64Kb SRAM CIM macro with INT4 and 8-bit weights", "It integrates 512 KB on-chip SRAM buffer.")
        self.assertEqual((s["mem"], s["prec"]), (8000.0, 8))

    def test_derived(self):
        self.assertEqual(C.derived({"thr": 4.0, "area": 2.0, "p": 0.5}), {"aeff_calc": 2.0, "eff_calc": 8.0})

    def test_type_arch_app(self):
        t = "A 28nm 69.4TOPS/W Product-Cache-based Digital-Compute-in-Memory Macro for Transformer Inference"
        self.assertEqual(C.accel_type(t, ""), "CIM/PIM")
        self.assertIn("Digital CIM", C.architectures(t, ""))
        self.assertIn("Transformer/LLM", C.applications(t, ""))
        self.assertEqual(C.accel_type("HWSA: A Weight Sparse Accelerator for CNN Inference", ""), "Digital")
        self.assertTrue(C.is_silicon("An architecture", "", "ISSCC"))
        self.assertFalse(C.is_silicon("An architecture", "We simulate it with gem5.", "MICRO"))
        self.assertTrue(C.is_silicon("An architecture", "A test chip was fabricated in 28-nm CMOS.", "MICRO"))


class TestBuild(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cache = os.path.join(self.tmp, "cache")
        os.makedirs(self.cache)
        self._papers, self._meta = build.PAPERS, build.META
        build.PAPERS = os.path.join(self.tmp, "papers.json")
        build.META = os.path.join(self.tmp, "meta.json")

    def tearDown(self):
        build.PAPERS, build.META = self._papers, self._meta
        shutil.rmtree(self.tmp)

    def put(self, n, title, pub, abstract="", year=2025):
        with open(os.path.join(self.cache, "%d.json" % n), "w", encoding="utf-8") as f:
            json.dump({"article_number": n, "title": title, "publication_title": pub, "abstract": abstract,
                       "publication_year": year, "publication_date": "Feb. %d" % year, "doi": "10.1109/x.%d" % n,
                       "authors": {"authors": [{"full_name": "A. Kim", "author_order": 1,
                                                "affiliation": "KAIST, Daejeon, South Korea"}]}}, f)

    def test_rebuild(self):
        config = build.load_json(build.CONFIG, None)
        self.put(1, "A 4.1-TOPS Sparse CNN Accelerator", "IEEE Journal of Solid-State Circuits",
                 "It consumes 500 mW in 22-nm CMOS and occupies 2 mm2.")
        self.put(2, "A 12-b SAR ADC", "IEEE Journal of Solid-State Circuits")
        self.put(3, "A Transformer Accelerator With Token Pruning", "2025 IEEE/ACM International Symposium on Microarchitecture (MICRO)")
        self.put(4, "A DNN Accelerator", "2025 28th Asia and South Pacific Design Automation Conference (ASP-DAC)")
        self.put(7, "A Mobile Application Processor in 4 nm", "IEEE Journal of Solid-State Circuits", "It integrates an NPU.")
        self.put(5, "An Old Neural Network Processor", "IEEE Journal of Solid-State Circuits", year=2005)
        meta = build.rebuild(config, self.cache, "2026-10-24")
        papers = {p["id"]: p for p in build.load_json(build.PAPERS, [])}
        self.assertEqual(set(papers), {"1", "3", "7"})
        self.assertEqual((papers["7"]["lv"], papers["7"]["s"], papers["7"]["sys"]), ("related", {}, True))
        p = papers["1"]
        self.assertEqual((p["v"], p["ty"], p["si"], p["cn"], p["x"]["eff_calc"], p["x"]["aeff_calc"]),
                         ("JSSC", "Digital", True, ["South Korea"], 8.2, 2.05))
        self.assertEqual((papers["3"]["v"], papers["3"]["si"]), ("MICRO", False))
        self.assertNotIn("abstract", json.dumps(list(papers.values())))
        self.assertEqual((meta["core"], meta["silicon"], meta["last_run_new"]), (2, 1, 0))


if __name__ == "__main__":
    unittest.main()
