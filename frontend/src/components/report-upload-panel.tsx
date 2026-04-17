import { useRef, useState } from "react"
import { FileUpIcon, LoaderCircleIcon, XIcon } from "lucide-react"
import { Button } from "@/components/ui/button"

export function ReportUploadPanel({
  disabled = false,
  fileNames,
  onFilesSelected,
  onClear,
}: {
  disabled?: boolean
  fileNames: string[]
  onFilesSelected: (files: File[]) => Promise<void> | void
  onClear: () => void
}) {
  const inputRef = useRef<HTMLInputElement | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const handleFiles = async (fileList: FileList | null) => {
    const files = [...(fileList ?? [])].filter((file) =>
      file.name.toLowerCase().endsWith(".csv")
    )
    if (files.length === 0) {
      return
    }

    setIsLoading(true)
    try {
      await onFilesSelected(files)
      if (inputRef.current) {
        inputRef.current.value = ""
      }
    } finally {
      setIsLoading(false)
      setIsDragging(false)
    }
  }

  return (
    <section
      className={
        isDragging
          ? "rounded-[1.6rem] border border-dashed border-primary/60 bg-primary/5 p-4 shadow-sm transition"
          : "rounded-[1.6rem] border border-dashed border-border/70 bg-card/80 p-4 shadow-sm transition"
      }
      onDragOver={(event) => {
        event.preventDefault()
        if (!disabled && !isLoading) {
          setIsDragging(true)
        }
      }}
      onDragLeave={(event) => {
        event.preventDefault()
        if (event.currentTarget.contains(event.relatedTarget as Node | null)) {
          return
        }
        setIsDragging(false)
      }}
      onDrop={(event) => {
        event.preventDefault()
        if (disabled || isLoading) {
          setIsDragging(false)
          return
        }
        void handleFiles(event.dataTransfer.files)
      }}
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary/75">
            Upload MRIQC CSV
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            Drag and drop `T1w.csv`, `T2w.csv`, or `bold.csv`, or choose files manually.
          </p>
          {fileNames.length > 0 ? (
            <p className="mt-2 text-xs text-foreground">
              Loaded: {fileNames.join(", ")}
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            ref={inputRef}
            type="file"
            accept=".csv,text/csv"
            multiple
            className="sr-only"
            onChange={(event) => void handleFiles(event.target.files)}
          />
          <Button
            type="button"
            variant="outline"
            className="rounded-xl"
            disabled={disabled || isLoading}
            onClick={() => inputRef.current?.click()}
          >
            {isLoading ? (
              <LoaderCircleIcon className="size-4 animate-spin" />
            ) : (
              <FileUpIcon className="size-4" />
            )}
            Choose files
          </Button>
          {fileNames.length > 0 ? (
            <Button
              type="button"
              variant="ghost"
              className="rounded-xl"
              onClick={onClear}
              disabled={isLoading}
            >
              <XIcon className="size-4" />
              Clear upload
            </Button>
          ) : null}
        </div>
      </div>
    </section>
  )
}
