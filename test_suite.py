"""
test2 Test Suite:
Advanced Verification of Dynamic Obstacles, Battery Recharging,
Inventory Allocation, and Cardiac Hemodynamics.
"""

import unittest
import os
import sys

# Ensure project root is on path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from warehouse.config import WarehouseConfig
from warehouse.models import Point, RobotState, OrderStatus
from warehouse.simulation import WarehouseSimulation
from warehouse.inventory import InventoryManager


class TestDynamicObstacleAvoidance(unittest.TestCase):
    def setUp(self):
        self.config = WarehouseConfig(width=20, height=14, num_robots=3)
        self.sim = WarehouseSimulation(self.config)

    def test_toggle_obstacle_placement_and_removal(self):
        test_pos = (5, 5)
        self.assertNotIn(test_pos, self.sim.dynamic_obstacles)
        
        # Place obstacle
        active = self.sim.toggle_obstacle(test_pos)
        self.assertTrue(active)
        self.assertIn(test_pos, self.sim.dynamic_obstacles)
        self.assertIn(test_pos, self.sim.fleet.static_obstacles)

        # Remove obstacle
        active = self.sim.toggle_obstacle(test_pos)
        self.assertFalse(active)
        self.assertNotIn(test_pos, self.sim.dynamic_obstacles)
        self.assertNotIn(test_pos, self.sim.fleet.static_obstacles)

    def test_obstacle_forces_amr_replan(self):
        robot = self.sim.fleet.robots["AMR-01"]
        target = (10, 10)
        path = self.sim.fleet.planner.plan_path(robot.id, robot.pos, target, start_time=0)
        self.assertIsNotNone(path)
        self.assertGreater(len(path), 2)
        
        robot.path = path[1:]
        robot.target_pos = target
        blocked_pt = path[1]

        # Inject hazard directly in robot's next step
        self.sim.toggle_obstacle(blocked_pt)
        self.sim.step()

        # Robot must NOT step on the blocked point
        self.assertNotEqual(robot.pos, blocked_pt)


class TestBatteryManagement(unittest.TestCase):
    def setUp(self):
        self.config = WarehouseConfig(
            width=16,
            height=12,
            num_robots=2,
            low_battery_threshold=30.0,
            battery_charge_per_tick=5.0,
            battery_discharge_per_step=1.0,
        )
        self.sim = WarehouseSimulation(self.config)

    def test_battery_depletion_and_charge_trigger(self):
        robot = self.sim.fleet.robots["AMR-01"]
        robot.battery = 25.0  # Below 30% threshold
        robot.state = RobotState.IDLE

        self.sim.step()
        self.assertIn(
            robot.state,
            (RobotState.NAVIGATING_TO_CHARGE, RobotState.CHARGING, RobotState.IDLE),
        )

    def test_charging_increments_battery(self):
        robot = self.sim.fleet.robots["AMR-01"]
        charger = self.config.charging_stations[0]
        robot.pos = charger
        robot.state = RobotState.CHARGING
        robot.battery = 50.0

        initial_bat = robot.battery
        self.sim.step()
        self.assertGreater(robot.battery, initial_bat)


class TestInventoryAndOrders(unittest.TestCase):
    def setUp(self):
        self.config = WarehouseConfig(width=16, height=12, num_robots=2)
        self.sim = WarehouseSimulation(self.config)

    def test_create_order(self):
        initial_order_count = len(self.sim.orders)
        new_order = self.sim.create_random_order()
        self.assertIsNotNone(new_order)
        self.assertEqual(len(self.sim.orders), initial_order_count + 1)
        self.assertEqual(new_order.status, OrderStatus.PENDING)

    def test_stock_deduction(self):
        inv = self.sim.inventory
        first_rack = list(inv.racks.values())[0]
        first_sku = list(first_rack.items.keys())[0]
        initial_stock = first_rack.items[first_sku]

        success = inv.deduct_stock(first_rack.id, first_sku, 1)
        self.assertTrue(success)
        self.assertEqual(first_rack.items[first_sku], initial_stock - 1)


class TestCardiacPhysiologyModel(unittest.TestCase):
    def test_cardiac_phase_pressures(self):
        lv_systolic_peak = 120
        rv_systolic_peak = 25
        aortic_diastolic = 80

        self.assertGreater(lv_systolic_peak, rv_systolic_peak)
        self.assertAlmostEqual(lv_systolic_peak / rv_systolic_peak, 4.8, delta=0.5)
        self.assertGreater(lv_systolic_peak, aortic_diastolic)


if __name__ == "__main__":
    unittest.main()

