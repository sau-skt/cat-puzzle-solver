"""Puzzle upload, board editing, solving, and history."""

from fastapi import APIRouter, File, Query, Response, UploadFile, status

from app.core.deps import DbSession, VerifiedUser
from app.schemas.puzzle import BoardResponse, BoardUpdate, PuzzleDetail, PuzzleListResponse, SolveResponse, SolutionResponse, StatsResponse
from app.services import puzzle_service

router = APIRouter(prefix="/puzzles", tags=["puzzles"])


@router.get("/stats", response_model=StatsResponse)
def puzzle_stats(user: VerifiedUser, db: DbSession) -> StatsResponse:
    return puzzle_service.stats_for(db, user)


@router.get("", response_model=PuzzleListResponse)
def list_puzzles(
    user: VerifiedUser,
    db: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PuzzleListResponse:
    return puzzle_service.list_puzzles(db, user, limit, offset)


@router.post("/upload", response_model=PuzzleDetail, status_code=status.HTTP_201_CREATED)
async def upload_puzzle(user: VerifiedUser, db: DbSession, file: UploadFile = File(...)) -> PuzzleDetail:
    return await puzzle_service.create_upload(db, user, file)


@router.post("/{puzzle_id}/analyze", response_model=BoardResponse)
def analyze(puzzle_id: str, user: VerifiedUser, db: DbSession) -> BoardResponse:
    return puzzle_service.analyze_puzzle(db, user, puzzle_id)


@router.get("/{puzzle_id}/image")
def puzzle_image(puzzle_id: str, user: VerifiedUser, db: DbSession) -> Response:
    payload, media = puzzle_service.puzzle_image(db, user, puzzle_id)
    return Response(content=payload, media_type=media)


@router.get("/{puzzle_id}/board", response_model=BoardResponse)
def get_board(puzzle_id: str, user: VerifiedUser, db: DbSession) -> BoardResponse:
    return puzzle_service.get_board(db, user, puzzle_id)


@router.put("/{puzzle_id}/board", response_model=BoardResponse)
def put_board(puzzle_id: str, payload: BoardUpdate, user: VerifiedUser, db: DbSession) -> BoardResponse:
    return puzzle_service.update_board(db, user, puzzle_id, payload)


@router.post("/{puzzle_id}/solve", response_model=SolveResponse)
def solve(puzzle_id: str, user: VerifiedUser, db: DbSession) -> SolveResponse:
    return puzzle_service.solve_puzzle(db, user, puzzle_id)


@router.get("/{puzzle_id}/solutions", response_model=list[SolutionResponse])
def list_solutions(puzzle_id: str, user: VerifiedUser, db: DbSession) -> list[SolutionResponse]:
    return puzzle_service.list_solutions(db, user, puzzle_id)


@router.get("/{puzzle_id}/solutions/{solution_id}", response_model=SolutionResponse)
def get_solution(puzzle_id: str, solution_id: str, user: VerifiedUser, db: DbSession) -> SolutionResponse:
    return puzzle_service.get_solution(db, user, puzzle_id, solution_id)


@router.get("/{puzzle_id}/solutions/{solution_id}/image")
def solution_image(puzzle_id: str, solution_id: str, user: VerifiedUser, db: DbSession) -> Response:
    payload = puzzle_service.solution_png(db, user, puzzle_id, solution_id)
    return Response(
        content=payload,
        media_type="image/png",
        headers={"Content-Disposition": 'inline; filename="cat-puzzle-solution.png"'},
    )


@router.get("/{puzzle_id}", response_model=PuzzleDetail)
def get_puzzle(puzzle_id: str, user: VerifiedUser, db: DbSession) -> PuzzleDetail:
    return puzzle_service.get_puzzle(db, user, puzzle_id)


@router.delete("/{puzzle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_puzzle(puzzle_id: str, user: VerifiedUser, db: DbSession) -> Response:
    puzzle_service.delete_puzzle(db, user, puzzle_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
