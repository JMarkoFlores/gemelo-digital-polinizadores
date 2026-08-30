from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from mesa import Agent, Model
from mesa.space import MultiGrid
from mesa.time import RandomActivation


@dataclass
class ABMScenario:
    width: int = 18
    height: int = 18
    steps: int = 30
    initial_pollinators: int = 55
    crop_area_pct: float = 60.0
    natural_area_pct: float = 22.0
    floral_strips_pct: float = 8.0
    pesticide_level: float = 28.0
    soil_management_score: float = 70.0
    temperature_c: float = 24.0
    landscape_diversity: float = 0.65
    seed: int = 42


class PollinatorAgent(Agent):
    def __init__(self, model: "PollinatorLandscapeModel", energy: float) -> None:
        super().__init__(model.next_id(), model)
        self.energy = energy
        self.visited_resources = 0.0

    def _best_neighbor(self) -> tuple[int, int]:
        neighbors = self.model.grid.get_neighborhood(self.pos, moore=True, include_center=True)
        return max(neighbors, key=lambda cell: self.model.resource_map[cell[0], cell[1]] + self.random.random())

    def step(self) -> None:
        target = self._best_neighbor()
        self.model.grid.move_agent(self, target)
        resource = self.model.consume_resource(target)
        hazard = self.model.hazard_map[target[0], target[1]]
        self.energy += resource - hazard - 0.4
        self.visited_resources += resource

        if self.energy > 6.2 and self.random.random() < self.model.reproduction_probability:
            self.energy *= 0.55
            offspring = PollinatorAgent(self.model, energy=self.energy)
            self.model.grid.place_agent(offspring, self.pos)
            self.model.schedule.add(offspring)

        if self.energy <= 0.35:
            self.model.grid.remove_agent(self)
            self.model.schedule.remove(self)


class PollinatorLandscapeModel(Model):
    def __init__(self, scenario: ABMScenario) -> None:
        super().__init__(seed=scenario.seed)
        self.scenario = scenario
        self.grid = MultiGrid(scenario.width, scenario.height, torus=False)
        self.schedule = RandomActivation(self)
        self.resource_map = np.zeros((scenario.width, scenario.height), dtype=float)
        self.hazard_map = np.zeros((scenario.width, scenario.height), dtype=float)
        self.habitat_map = np.full((scenario.width, scenario.height), "crop", dtype=object)
        self.resource_history: list[np.ndarray] = []
        self.population_history: list[int] = []
        self.reproduction_probability = min(0.34, 0.12 + scenario.landscape_diversity * 0.18)
        self._build_landscape()
        self._seed_agents()

    def _build_landscape(self) -> None:
        total_cells = self.scenario.width * self.scenario.height
        natural_cells = int(total_cells * (self.scenario.natural_area_pct / 100.0))
        floral_cells = int(total_cells * (self.scenario.floral_strips_pct / 100.0))

        positions = [(x, y) for x in range(self.scenario.width) for y in range(self.scenario.height)]
        self.random.shuffle(positions)

        natural_positions = set(positions[:natural_cells])
        floral_positions = set(positions[natural_cells : natural_cells + floral_cells])

        for x, y in positions:
            if (x, y) in natural_positions:
                self.habitat_map[x, y] = "natural"
                self.resource_map[x, y] = 3.6 + self.random.random() * 1.4
                self.hazard_map[x, y] = max(0.08, self.scenario.pesticide_level / 420.0)
            elif (x, y) in floral_positions:
                self.habitat_map[x, y] = "floral"
                self.resource_map[x, y] = 3.1 + self.random.random() * 1.2
                self.hazard_map[x, y] = max(0.12, self.scenario.pesticide_level / 340.0)
            else:
                self.resource_map[x, y] = 1.0 + self.random.random() * 0.9
                self.hazard_map[x, y] = 0.35 + self.scenario.pesticide_level / 150.0

        heat_penalty = max(0.0, abs(self.scenario.temperature_c - 24.0) * 0.08)
        soil_bonus = self.scenario.soil_management_score / 500.0
        self.resource_map = np.clip(self.resource_map + soil_bonus - heat_penalty, 0.2, None)

    def _seed_agents(self) -> None:
        for _ in range(self.scenario.initial_pollinators):
            energy = 3.0 + self.random.random() * 1.8
            agent = PollinatorAgent(self, energy=energy)
            pos = (self.random.randrange(self.scenario.width), self.random.randrange(self.scenario.height))
            self.grid.place_agent(agent, pos)
            self.schedule.add(agent)

    def consume_resource(self, pos: tuple[int, int]) -> float:
        x, y = pos
        value = min(self.resource_map[x, y], 1.65)
        self.resource_map[x, y] = max(0.12, self.resource_map[x, y] - 0.22)
        return value

    def step(self) -> None:
        regen = np.where(self.habitat_map == "natural", 0.24, np.where(self.habitat_map == "floral", 0.18, 0.08))
        self.resource_map = np.clip(self.resource_map + regen, 0.2, 5.0)
        self.schedule.step()
        self.population_history.append(self.schedule.get_agent_count())
        self.resource_history.append(self.resource_map.copy())

    def run(self) -> dict[str, float | list[int] | np.ndarray]:
        for _ in range(self.scenario.steps):
            if self.schedule.get_agent_count() == 0:
                break
            self.step()

        final_population = self.schedule.get_agent_count()
        diversity = (
            8
            + self.scenario.natural_area_pct * 0.38
            + self.scenario.floral_strips_pct * 0.55
            + self.scenario.landscape_diversity * 14
            - self.scenario.pesticide_level * 0.08
        )
        diversity = float(np.clip(diversity, 4, 55))
        return {
            "final_population": float(final_population),
            "mean_population": float(np.mean(self.population_history) if self.population_history else final_population),
            "diversity_index": diversity,
            "resource_map": self.resource_history[-1] if self.resource_history else self.resource_map,
            "population_history": self.population_history,
            "habitat_map": self.habitat_map,
        }


def run_example_simulation(scenario: ABMScenario) -> dict[str, float | list[int] | np.ndarray]:
    model = PollinatorLandscapeModel(scenario)
    return model.run()


def enrich_dataset_with_abm(dataframe: pd.DataFrame, random_state: int = 42) -> pd.DataFrame:
    enriched = dataframe.copy()
    abundance_values: list[float] = []
    diversity_values: list[float] = []

    sample_limit = min(len(enriched), 120)
    for index, row in enriched.iloc[:sample_limit].iterrows():
        scenario = ABMScenario(
            crop_area_pct=float(row["crop_area_pct"]),
            natural_area_pct=float(row["natural_area_pct"]),
            floral_strips_pct=float(row["floral_strips_pct"]),
            pesticide_level=float(row["pesticide_level"]),
            soil_management_score=float(row["soil_management_score"]),
            temperature_c=float(row["temperature_c"]),
            landscape_diversity=float(row["landscape_diversity"]),
            initial_pollinators=max(30, int(28 + row["natural_area_pct"] * 0.8)),
            seed=random_state + int(index),
        )
        result = run_example_simulation(scenario)
        abundance_values.append(float(np.clip(result["mean_population"] * 1.25, 8, 120)))
        diversity_values.append(float(result["diversity_index"]))

    if sample_limit < len(enriched):
        tail = enriched.iloc[sample_limit:]
        abundance_values.extend(tail["pollinator_abundance_index"].tolist())
        diversity_values.extend(tail["pollinator_diversity_index"].tolist())

    enriched["abm_pollinator_abundance"] = np.round(abundance_values, 2)
    enriched["abm_pollinator_diversity"] = np.round(diversity_values, 2)
    enriched["pollinator_abundance_index"] = np.round(
        enriched["pollinator_abundance_index"] * 0.35 + enriched["abm_pollinator_abundance"] * 0.65,
        2,
    )
    enriched["pollinator_diversity_index"] = np.round(
        enriched["pollinator_diversity_index"] * 0.3 + enriched["abm_pollinator_diversity"] * 0.7,
        2,
    )
    enriched["crop_yield_index"] = np.round(
        enriched["crop_yield_index"] + enriched["pollinator_abundance_index"] * 0.03,
        2,
    )
    return enriched
