import { ImagePlus, X } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Alert, Button } from "../components/ui";
import { api, errorMessage } from "../services/api";
import type { PuzzleDetail } from "../types";

const TYPES = ["image/png", "image/jpeg", "image/webp"];

export function UploadPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [progress, setProgress] = useState<number | null>(null);

  function choose(next: File | null) {
    setError("");
    if (!next) return;
    if (!TYPES.includes(next.type) && !/\.(png|jpe?g|webp)$/i.test(next.name)) {
      setError("Use a PNG, JPG, JPEG, or WEBP screenshot.");
      return;
    }
    if (next.size > 8 * 1024 * 1024) {
      setError("Images must be 8 MB or smaller.");
      return;
    }
    if (preview) URL.revokeObjectURL(preview);
    setFile(next);
    setPreview(URL.createObjectURL(next));
  }

  function clear() {
    if (preview) URL.revokeObjectURL(preview);
    setFile(null);
    setPreview(null);
    setProgress(null);
  }

  async function upload() {
    if (!file) return;
    setError("");
    const body = new FormData();
    body.append("file", file);
    try {
      const response = await api.post<PuzzleDetail>("/puzzles/upload", body, {
        onUploadProgress: (event) => {
          if (event.total) setProgress(Math.round((event.loaded / event.total) * 100));
        },
      });
      navigate(`/puzzles/${response.data.id}`);
    } catch (err) {
      setError(errorMessage(err));
      setProgress(null);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h1 className="font-display text-4xl">Upload a puzzle</h1>
      <p className="text-ink/70">
        Drop a screenshot of the colored board. A new upload replaces the previous image, its grid, and any saved solution.
      </p>
      {error ? <Alert>{error}</Alert> : null}
      <label
        className="grid cursor-pointer place-items-center rounded-[28px] border border-dashed border-ink/30 bg-paper px-6 py-14 text-center"
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          choose(event.dataTransfer.files?.[0] ?? null);
        }}
      >
        <ImagePlus className="text-amber-dark" />
        <span className="mt-2 font-semibold">Drag a screenshot here, or browse</span>
        <span className="text-sm text-ink/60">PNG, JPG, JPEG, WEBP · 8 MB max</span>
        <input
          className="sr-only"
          type="file"
          accept="image/png,image/jpeg,image/webp"
          onChange={(event) => choose(event.target.files?.[0] ?? null)}
        />
      </label>
      {preview ? (
        <div className="rounded-3xl border border-line bg-paper p-4">
          <div className="mb-3 flex items-center justify-between">
            <p className="truncate text-sm font-semibold">{file?.name}</p>
            <button onClick={clear} aria-label="Remove image">
              <X size={16} />
            </button>
          </div>
          <img src={preview} alt="Selected puzzle screenshot" className="max-h-80 w-full rounded-2xl object-contain" />
          {progress !== null ? <p className="mt-3 text-sm">Uploading {progress}%</p> : null}
          <div className="mt-4 flex gap-2">
            <Button onClick={upload} disabled={progress !== null && progress < 100}>
              Analyze this board
            </Button>
            <Button variant="ghost" onClick={clear}>
              Choose another
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
