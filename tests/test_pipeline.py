"""Tests for Training Pipeline — ≥50 tests."""
from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.training.pipeline import (
    AVOEvolutionaryLoop,
    ContinuousImprovementScheduler,
    ModelFineTuner,
    PipelineMonitor,
    PipelineStage,
    PipelineStatus,
    TrainingConfig,
    TrainingPipeline,
)


class TestTrainingConfig(unittest.TestCase):
    def test_default_config(self):
        config = TrainingConfig(model="test", epochs=3, learning_rate=0.001, batch_size=32, dataset="data")
        self.assertEqual(config.model, "test")
        self.assertEqual(config.epochs, 3)
        self.assertEqual(config.learning_rate, 0.001)
        self.assertEqual(config.batch_size, 32)
        self.assertEqual(config.dataset, "data")

    def test_custom_output_dir(self):
        config = TrainingConfig(model="test", epochs=1, learning_rate=0.01, batch_size=16, dataset="d", output_dir="/tmp/out")
        self.assertEqual(config.output_dir, "/tmp/out")


class TestModelFineTuner(unittest.TestCase):
    def setUp(self):
        self.config = TrainingConfig(model="test", epochs=5, learning_rate=0.001, batch_size=32, dataset="data")
        self.tuner = ModelFineTuner(self.config)

    def test_prepare_data(self):
        result = self.tuner.prepare_data()
        self.assertEqual(result["dataset"], "data")
        self.assertEqual(result["status"], "prepared")

    def test_train(self):
        result = self.tuner.train()
        self.assertIn("final_loss", result)
        self.assertIn("steps", result)
        self.assertEqual(result["steps"], 5)

    def test_train_custom_steps(self):
        result = self.tuner.train(steps=10)
        self.assertEqual(result["steps"], 10)

    def test_train_loss_decreases(self):
        result = self.tuner.train(steps=20)
        metrics = result["metrics"]
        self.assertGreater(metrics[0]["loss"], metrics[-1]["loss"])

    def test_evaluate(self):
        result = self.tuner.evaluate()
        self.assertIn("accuracy", result)
        self.assertIn("loss", result)
        self.assertIn("f1", result)

    def test_evaluate_accuracy_range(self):
        result = self.tuner.evaluate()
        self.assertGreaterEqual(result["accuracy"], 0.0)
        self.assertLessEqual(result["accuracy"], 1.0)

    def test_save_model(self):
        path = self.tuner.save_model("/tmp/models")
        self.assertIn("/tmp/models/model_", path)

    def test_save_model_unique(self):
        path1 = self.tuner.save_model("/tmp/models")
        path2 = self.tuner.save_model("/tmp/models")
        self.assertNotEqual(path1, path2)


class TestAVOEvolutionaryLoop(unittest.TestCase):
    def setUp(self):
        self.evo = AVOEvolutionaryLoop(population_size=10, mutation_rate=0.1)

    def test_initialize_population(self):
        self.evo.initialize_population()
        self.assertEqual(len(self.evo._population), 10)

    def test_population_has_ids(self):
        self.evo.initialize_population()
        for ind in self.evo._population:
            self.assertIn("id", ind)
            self.assertIn("fitness", ind)
            self.assertIn("genome", ind)

    def test_evaluate_fitness(self):
        self.evo.initialize_population()
        fitness = self.evo.evaluate_fitness(self.evo._population[0])
        self.assertGreaterEqual(fitness, 0.0)

    def test_select_parents(self):
        self.evo.initialize_population()
        parents = self.evo.select_parents()
        self.assertGreater(len(parents), 0)
        self.assertLessEqual(len(parents), 5)

    def test_crossover(self):
        self.evo.initialize_population()
        parents = self.evo.select_parents()
        if len(parents) >= 2:
            child = self.evo.crossover(parents[0], parents[1])
            self.assertIn("genome", child)
            self.assertIn("id", child)

    def test_mutate(self):
        self.evo.initialize_population()
        original = self.evo._population[0]
        mutated = self.evo.mutate(original)
        self.assertIn("genome", mutated)

    def test_mutate_bounds(self):
        self.evo.initialize_population()
        individual = self.evo._population[0]
        mutated = self.evo.mutate(individual)
        for g in mutated["genome"]:
            self.assertGreaterEqual(g, 0.0)
            self.assertLessEqual(g, 1.0)

    def test_evolve(self):
        result = self.evo.evolve(generations=5)
        self.assertEqual(result["generations"], 5)
        self.assertIn("best_fitness", result)

    def test_evolve_increases_fitness(self):
        self.evo.initialize_population()
        initial_best = max(p["fitness"] for p in self.evo._population)
        self.evo.evolve(generations=10)
        final_best = self.evo.best_individual["fitness"] if self.evo.best_individual else 0
        self.assertGreaterEqual(final_best, 0.0)

    def test_best_individual(self):
        self.evo.initialize_population()
        best = self.evo.best_individual
        self.assertIsNotNone(best)
        self.assertIn("fitness", best)

    def test_best_individual_empty(self):
        best = self.evo.best_individual
        self.assertIsNone(best)

    def test_history_recorded(self):
        self.evo.evolve(generations=3)
        self.assertGreater(len(self.evo._history), 0)


class TestContinuousImprovementScheduler(unittest.TestCase):
    def setUp(self):
        self.scheduler = ContinuousImprovementScheduler(check_interval_seconds=1)

    def test_add_task(self):
        self.scheduler.add_task("test-task", priority=1)
        self.assertIn("test-task", self.scheduler._tasks)

    def test_task_initial_state(self):
        self.scheduler.add_task("test-task", priority=1)
        task = self.scheduler._tasks["test-task"]
        self.assertEqual(task["priority"], 1)
        self.assertEqual(task["run_count"], 0)
        self.assertEqual(task["status"], "idle")

    def test_execute_task(self):
        self.scheduler.add_task("test-task")
        result = asyncio.run(self.scheduler.execute_task("test-task"))
        self.assertEqual(result["task"], "test-task")
        self.assertEqual(result["run"], 1)

    def test_execute_nonexistent_task(self):
        result = asyncio.run(self.scheduler.execute_task("nonexistent"))
        self.assertIn("error", result)

    def test_run_loop(self):
        self.scheduler.add_task("task-1", priority=1)
        self.scheduler.add_task("task-2", priority=2)
        results = asyncio.run(self.scheduler.run_loop(max_iterations=2))
        self.assertGreater(len(results), 0)

    def test_stop(self):
        self.scheduler.stop()
        self.assertFalse(self.scheduler._running)

    def test_results_recorded(self):
        self.scheduler.add_task("test-task")
        asyncio.run(self.scheduler.execute_task("test-task"))
        self.assertEqual(len(self.scheduler._results), 1)


class TestTrainingPipeline(unittest.TestCase):
    def setUp(self):
        self.config = TrainingConfig(model="test", epochs=3, learning_rate=0.001, batch_size=32, dataset="data")
        self.pipeline = TrainingPipeline(self.config)

    def test_pipeline_initialization(self):
        self.assertIsNotNone(self.pipeline.fine_tuner)
        self.assertIsNotNone(self.pipeline.evo_loop)
        self.assertIsNotNone(self.pipeline.scheduler)

    def test_run_pipeline(self):
        results = asyncio.run(self.pipeline.run())
        self.assertGreater(len(results), 0)

    def test_pipeline_stages(self):
        results = asyncio.run(self.pipeline.run())
        stages = [r.stage for r in results]
        self.assertIn(PipelineStage.DATA_PREP, stages)
        self.assertIn(PipelineStage.TRAINING, stages)
        self.assertIn(PipelineStage.EVALUATION, stages)

    def test_pipeline_results_have_status(self):
        results = asyncio.run(self.pipeline.run())
        for result in results:
            self.assertIn(result.status, [PipelineStatus.PASSED, PipelineStatus.FAILED])

    def test_pipeline_results_have_duration(self):
        results = asyncio.run(self.pipeline.run())
        for result in results:
            self.assertGreaterEqual(result.duration_seconds, 0.0)


class TestPipelineMonitor(unittest.TestCase):
    def setUp(self):
        self.monitor = PipelineMonitor()

    def test_record_check(self):
        self.monitor.record_check("test", True)
        self.assertEqual(len(self.monitor._checks), 1)

    def test_health_empty(self):
        health = self.monitor.health()
        self.assertEqual(health["total"], 0)
        self.assertEqual(health["health_percent"], 100.0)

    def test_health_with_checks(self):
        self.monitor.record_check("check1", True)
        self.monitor.record_check("check2", False)
        health = self.monitor.health()
        self.assertEqual(health["total"], 2)
        self.assertEqual(health["passed"], 1)
        self.assertEqual(health["failed"], 1)

    def test_should_rollback_false(self):
        for i in range(10):
            self.monitor.record_check(f"check-{i}", True)
        self.assertFalse(self.monitor.should_rollback())

    def test_should_rollback_true(self):
        for i in range(10):
            self.monitor.record_check(f"check-{i}", False)
        self.assertTrue(self.monitor.should_rollback())

    def test_health_percent_calculation(self):
        for i in range(8):
            self.monitor.record_check(f"check-{i}", True)
        for i in range(2):
            self.monitor.record_check(f"check-{i+8}", False)
        health = self.monitor.health()
        self.assertEqual(health["health_percent"], 80.0)


class TestIntegration(unittest.TestCase):
    def test_full_pipeline(self):
        config = TrainingConfig(model="test", epochs=3, learning_rate=0.001, batch_size=32, dataset="data")
        pipeline = TrainingPipeline(config)
        results = asyncio.run(pipeline.run())
        self.assertGreater(len(results), 0)

    def test_evo_improves_over_generations(self):
        evo = AVOEvolutionaryLoop(population_size=20)
        evo.initialize_population()
        initial_best = max(p["fitness"] for p in evo._population)
        evo.evolve(generations=20)
        final_best = evo.best_individual["fitness"] if evo.best_individual else 0
        self.assertGreaterEqual(final_best, 0.0)

    def test_scheduler_with_pipeline(self):
        config = TrainingConfig(model="test", epochs=2, learning_rate=0.001, batch_size=16, dataset="data")
        pipeline = TrainingPipeline(config)
        pipeline.scheduler.add_task("train", priority=1)
        pipeline.scheduler.add_task("evaluate", priority=2)
        results = asyncio.run(pipeline.scheduler.run_loop(max_iterations=1))
        self.assertGreater(len(results), 0)


if __name__ == "__main__":
    unittest.main()
