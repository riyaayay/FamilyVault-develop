"use client";

import * as React from "react";
import { UploadCloud, X, Loader2, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

const BIOMETRICS_URL =
  process.env.NEXT_PUBLIC_BIOMETRICS_API_URL ?? "http://localhost:18002";

export function MediaUploadWidget() {
  const [file, setFile] = React.useState<File | null>(null);
  const [status, setStatus] = React.useState<"idle" | "uploading" | "success" | "error">("idle");
  const [message, setMessage] = React.useState("");

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setStatus("idle");
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setStatus("uploading");
    
    try {
      // 1. Get presigned URL
      const urlRes = await fetch(`${BIOMETRICS_URL}/api/v1/biometrics/upload-url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          file_name: file.name,
          content_type: file.type || "application/octet-stream",
        }),
      });
      
      if (!urlRes.ok) throw new Error("Failed to get upload URL");
      const urlData = await urlRes.json();
      
      // 2. Upload to R2
      const uploadRes = await fetch(urlData.upload_url, {
        method: "PUT",
        headers: { "Content-Type": file.type || "application/octet-stream" },
        body: file,
      });
      
      if (!uploadRes.ok) throw new Error("Failed to upload to R2");
      
      // 3. Match faces and route
      let mediaType = "document";
      if (file.type.startsWith("image/")) mediaType = "image";
      else if (file.type.startsWith("video/")) mediaType = "video";
      else if (file.type.startsWith("audio/")) mediaType = "audio";
      else if (file.type.includes("pdf")) mediaType = "pdf";
      else if (file.type.includes("word") || file.type.includes("document")) mediaType = "docx";

      const matchRes = await fetch(`${BIOMETRICS_URL}/api/v1/biometrics/match`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          media_id: `media_${Date.now()}`,
          r2_url: urlData.public_url,
          media_type: mediaType,
        }),
      });
      
      if (!matchRes.ok) {
        const errorData = await matchRes.json();
        throw new Error(errorData.detail || "Failed to process media");
      }
      
      const matchData = await matchRes.json();
      setStatus("success");
      setMessage(matchData.status || "Media successfully uploaded and routed.");
      setFile(null);
    } catch (err) {
      setStatus("error");
      setMessage(err instanceof Error ? err.message : "An error occurred during upload");
    }
  };

  return (
    <div className="border border-border rounded-lg p-5 bg-card mt-6">
      <div className="flex items-center gap-2 mb-4">
        <UploadCloud className="w-5 h-5 text-muted-foreground" />
        <h3 className="text-sm font-medium text-foreground">Upload Vault Media</h3>
      </div>
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-4">
          <input 
            type="file" 
            onChange={handleFileChange} 
            className="text-sm text-muted-foreground file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-muted file:text-foreground hover:file:bg-muted/80 cursor-pointer"
          />
          <Button 
            onClick={handleUpload} 
            disabled={!file || status === "uploading"}
            size="sm"
          >
            {status === "uploading" ? (
              <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Uploading...</>
            ) : (
              "Upload to Vault"
            )}
          </Button>
        </div>
        {status === "success" && (
          <p className="text-sm text-green-600 flex items-center gap-1.5 bg-green-500/10 p-2 rounded-md w-fit">
            <CheckCircle className="w-4 h-4" /> {message}
          </p>
        )}
        {status === "error" && (
          <p className="text-sm text-red-600 flex items-center gap-1.5 bg-red-500/10 p-2 rounded-md w-fit">
            <X className="w-4 h-4" /> {message}
          </p>
        )}
      </div>
    </div>
  );
}
