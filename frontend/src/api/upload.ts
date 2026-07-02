import COS from "cos-js-sdk-v5";
import client from "./client";
import type { UploadCredential, UploadPurpose } from "@/types";

const STANDARD_IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp", "image/gif"]);
const IOS_HEIC_TYPES = new Set(["image/heic", "image/heif"]);

function inferImageType(fileName: string) {
  const suffix = fileName.split(".").pop()?.toLowerCase() || "";
  if (suffix === "jpg" || suffix === "jpeg") return "image/jpeg";
  if (suffix === "png") return "image/png";
  if (suffix === "webp") return "image/webp";
  if (suffix === "gif") return "image/gif";
  if (suffix === "heic") return "image/heic";
  if (suffix === "heif") return "image/heif";
  return "";
}

function replaceImageExt(fileName: string, nextExt: string) {
  const baseName = fileName.replace(/\.[^.]+$/, "") || "image";
  return `${baseName}.${nextExt}`;
}

function canvasToBlob(canvas: HTMLCanvasElement, type: string, quality?: number) {
  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (!blob) {
        reject(new Error("图片转换失败，请更换图片后重试"));
        return;
      }
      resolve(blob);
    }, type, quality);
  });
}

function loadImageFromObjectUrl(objectUrl: string) {
  return new Promise<HTMLImageElement>((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("图片转换失败，请更换图片后重试"));
    image.src = objectUrl;
  });
}

async function convertImageToJpeg(file: File) {
  const objectUrl = URL.createObjectURL(file);
  try {
    const image = await loadImageFromObjectUrl(objectUrl);

    const canvas = document.createElement("canvas");
    canvas.width = image.naturalWidth || image.width;
    canvas.height = image.naturalHeight || image.height;
    const ctx = canvas.getContext("2d");
    if (!ctx || !canvas.width || !canvas.height) {
      throw new Error("图片转换失败，请更换图片后重试");
    }

    ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
    const blob = await canvasToBlob(canvas, "image/jpeg", 0.92);
    return new File([blob], replaceImageExt(file.name, "jpg"), {
      type: "image/jpeg",
      lastModified: file.lastModified,
    });
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

export async function normalizeImageFileForUpload(file: File) {
  const inferredType = inferImageType(file.name);
  const contentType = file.type || inferredType;

  if (STANDARD_IMAGE_TYPES.has(contentType)) {
    if (file.type === contentType) return file;
    return new File([file], file.name, {
      type: contentType,
      lastModified: file.lastModified,
    });
  }

  if (IOS_HEIC_TYPES.has(contentType)) {
    try {
      return await convertImageToJpeg(file);
    } catch {
      return new File([file], file.name, {
        type: contentType,
        lastModified: file.lastModified,
      });
    }
  }

  return file;
}

function getUploadCredential(file: File, purpose: UploadPurpose): Promise<UploadCredential> {
  return client.post("/upload/credential", {
    file_name: file.name,
    file_size: file.size,
    content_type: file.type,
    purpose,
  });
}

export function uploadReferenceImage(
  file: File,
  purpose: UploadPurpose = "ref",
  onProgress?: (percent: number) => void,
): Promise<{ url: string; key: string }> {
  return new Promise(async (resolve, reject) => {
    try {
      const uploadFile = await normalizeImageFileForUpload(file);
      const credential = await getUploadCredential(uploadFile, purpose);
      const cos = new COS({
        getAuthorization(_, callback) {
          callback({
            TmpSecretId: credential.tmp_secret_id,
            TmpSecretKey: credential.tmp_secret_key,
            SecurityToken: credential.session_token,
            StartTime: credential.start_time || Math.floor(Date.now() / 1000),
            ExpiredTime: credential.expired_time,
          });
        },
      });

      cos.putObject(
        {
          Bucket: credential.bucket,
          Region: credential.region,
          Key: credential.key,
          Body: uploadFile,
          ContentType: uploadFile.type,
          onProgress(progressData) {
            onProgress?.((progressData.percent || 0) * 100);
          },
        },
        (err) => {
          if (err) {
            reject(err);
            return;
          }
          resolve({ url: credential.url, key: credential.key });
        },
      );
    } catch (error) {
      reject(error);
    }
  });
}
