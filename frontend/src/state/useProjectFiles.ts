import { useMemo, useState } from "react";
import type { FileItem } from "../api/orchestrator";

export function useProjectFiles() {
  const [files, setAllFiles] = useState<FileItem[]>([]);
  const [selectedPath, setSelectedPath] = useState<string>("");

  const selectedFile = useMemo(
    () => files.find((file) => file.path === selectedPath) ?? null,
    [files, selectedPath],
  );

  function setFiles(nextFiles: FileItem[]) {
    setAllFiles(nextFiles);
    if (nextFiles.length > 0) {
      setSelectedPath((prev) => (prev ? prev : nextFiles[0].path));
    } else {
      setSelectedPath("");
    }
  }

  return {
    files,
    setFiles,
    selectedPath,
    setSelectedPath,
    selectedFile,
  };
}
