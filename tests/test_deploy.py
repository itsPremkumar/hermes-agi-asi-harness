"""Tests for Deployment Manager and Daily Improvement."""
from __future__ import annotations

import asyncio
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from deploy import DailyImprovement, DeployConfig, DeploymentManager, DeployTarget


class TestDeploymentManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.deployer = DeploymentManager(self.temp_dir)

    def test_deploy_config_creation(self):
        config = DeployConfig(
            target=DeployTarget.DOCKER,
            image_name="test-app",
            tag="v1.0",
            replicas=3,
            ports={8080: 80},
        )
        self.assertEqual(config.target, DeployTarget.DOCKER)
        self.assertEqual(config.image_name, "test-app")

    def test_local_deploy(self):
        config = DeployConfig(target=DeployTarget.LOCAL, image_name="test")
        result = asyncio.run(self.deployer.deploy(config))
        self.assertEqual(result.status.value, "healthy")
        self.assertIsNotNone(result.end_time)

    def test_get_deploy(self):
        config = DeployConfig(target=DeployTarget.LOCAL, image_name="test")
        result = asyncio.run(self.deployer.deploy(config))
        fetched = self.deployer.get_deploy(result.deploy_id)
        self.assertIsNotNone(fetched)

    def test_list_deploys(self):
        for i in range(3):
            config = DeployConfig(target=DeployTarget.LOCAL, image_name=f"test-{i}")
            asyncio.run(self.deployer.deploy(config))
        deploys = self.deployer.list_deploys()
        self.assertEqual(len(deploys), 3)

    def test_health_check(self):
        config = DeployConfig(target=DeployTarget.LOCAL, image_name="test")
        result = asyncio.run(self.deployer.deploy(config))
        healthy = asyncio.run(self.deployer.health_check(result.deploy_id))
        self.assertTrue(healthy)

    def test_health_check_nonexistent(self):
        healthy = asyncio.run(self.deployer.health_check("nonexistent"))
        self.assertFalse(healthy)

    def test_stop_local_deploy_reaps_child(self):
        config = DeployConfig(target=DeployTarget.LOCAL, image_name="test")
        result = asyncio.run(self.deployer.deploy(config))
        self.assertIn(result.deploy_id, self.deployer._local_processes)
        self.assertTrue(self.deployer.stop(result.deploy_id))
        self.assertNotIn(result.deploy_id, self.deployer._local_processes)
        self.assertFalse(self.deployer.stop(result.deploy_id))
        self.assertFalse(self.deployer.stop("nonexistent"))


class TestDailyImprovement(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.improvement = DailyImprovement(self.temp_dir)

    def test_add_routine(self):
        self.improvement.add_routine("test", "Test task", "0 6 * * *")
        routines = self.improvement.list_routines()
        self.assertEqual(len(routines), 1)
        self.assertEqual(routines[0]["name"], "test")

    def test_run_routine(self):
        self.improvement.add_routine("test", "Test task", "0 6 * * *")
        result = asyncio.run(self.improvement.run_routine("test"))
        self.assertEqual(result["status"], "ok")

    def test_run_nonexistent_routine(self):
        result = asyncio.run(self.improvement.run_routine("nonexistent"))
        self.assertIn("error", result)

    def test_list_routines(self):
        for i in range(3):
            self.improvement.add_routine(f"routine-{i}", f"Task {i}", "0 * * * *")
        routines = self.improvement.list_routines()
        self.assertEqual(len(routines), 3)


if __name__ == "__main__":
    unittest.main()
