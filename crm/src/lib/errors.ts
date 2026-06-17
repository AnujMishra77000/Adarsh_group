import axios from "axios";

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const responseMessage = error.response?.data?.error?.message;
    if (typeof responseMessage === "string" && responseMessage.length > 0) {
      return responseMessage;
    }
    if (typeof error.response?.data?.detail === "string") {
      return error.response.data.detail;
    }
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Something went wrong. Please try again.";
}
