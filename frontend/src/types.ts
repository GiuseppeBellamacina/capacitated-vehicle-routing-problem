export interface InstanceInfo {
  name: string;
  dimension: number;
  capacity: number;
  num_vehicles: number;
  optimal: number | null;
}

export interface InstanceSet {
  set: string;
  instances: InstanceInfo[];
}

export interface Coord {
  x: number;
  y: number;
}

export interface WsProgress {
  type: "progress";
  run: number;
  generation: number;
  evaluations: number;
  best_cost: number;
  population_avg: number;
  routes?: number[][];
}

export interface WsRunStart {
  type: "run_start";
  run: number;
  total_runs: number;
  instance: string;
}

export interface WsRunComplete {
  type: "run_complete";
  run: number;
  cost: number;
  routes: number[][];
  generations_to_best: number;
  num_vehicles: number;
  evaluations: number;
}

export interface WsExperimentComplete {
  type: "experiment_complete";
  instance: string;
  optimal: number | null;
  best: number;
  mean: number;
  std_dev: number;
  runs: number[];
  routes: number[][];
  convergence: number[][];
  execution_time: number;
  generations_to_best: number[];
  max_evals?: number;
}

export type WsMessage =
  | WsProgress
  | WsRunStart
  | WsRunComplete
  | WsExperimentComplete
  | { type: "instances"; data: InstanceSet[] }
  | { type: "error"; message: string }
  | { type: "pong" }
  | { type: "experiment_cancelled"; completed_runs: number }
  | { type: "info"; message: string };

export interface Preset {
  label: string;
  description: string;
  variant:
    | "best"
    | "accent"
    | "small-preset"
    | "warning"
    | "danger"
    | "balanced"
    | "tuned";
  population_size: number;
  tournament_size: number;
  elite_count: number;
  granular_size: number;
  mutation_rate: number;
  crossover_rate: number;
  local_search_rate: number;
  local_search_max_iter: number;
}
