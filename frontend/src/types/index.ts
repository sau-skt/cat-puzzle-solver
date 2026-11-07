export type User = {
  id: string;
  full_name: string;
  email: string;
  is_verified: boolean;
  country_iso?: string | null;
  dial_code?: string | null;
  phone_number?: string | null;
  phone_e164?: string | null;
};

export type Rules = {
  one_per_row: boolean;
  one_per_column: boolean;
  one_per_color: boolean;
  no_touching: boolean;
};

export type Cell = {
  row: number;
  col: number;
  color_id: number | null;
  color_label: string | null;
  color_hex: string | null;
  blocked: boolean;
  has_cat: boolean;
  confidence: number;
  bbox_x?: number | null;
  bbox_y?: number | null;
  bbox_w?: number | null;
  bbox_h?: number | null;
};

export type Board = {
  puzzle_id: string;
  rows: number | null;
  cols: number | null;
  rules: Rules;
  cells: Cell[];
  detection_confidence: number | null;
  needs_review: boolean;
  notes: string[];
  status: string;
};

export type PuzzleSummary = {
  id: string;
  original_filename: string;
  status: string;
  rows: number | null;
  cols: number | null;
  solver_status: string | null;
  solution_count: number;
  detection_confidence: number | null;
  processing_time_ms: number | null;
  created_at: string;
  updated_at: string;
};

export type PuzzleDetail = PuzzleSummary & {
  needs_review: boolean;
  rules: Rules;
  notes: string[];
  solver_notes: string | null;
};

export type Placement = {
  cat: number;
  row: number;
  col: number;
  color_id: number | null;
  color_label: string | null;
  color_hex: string | null;
};

export type Solution = {
  id: string;
  index: number;
  placements: Placement[];
  validation_passed: boolean;
  execution_time_ms: number;
};

export type SolveResult = {
  puzzle_id: string;
  status: string;
  unique: boolean;
  solutions_found: number;
  truncated: boolean;
  timed_out: boolean;
  execution_time_ms: number;
  explanation: string | null;
  conflicts: string[];
  solutions: Solution[];
};

export type Stats = {
  total: number;
  solved: number;
  no_solution: number;
  in_progress: number;
  success_rate: number;
  recent: PuzzleSummary[];
};
