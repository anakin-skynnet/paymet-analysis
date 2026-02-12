/**
 * Open Databricks notebooks and folders using the backend API (credentials: include).
 * Use these instead of raw fetch so all requests go through the generated API client.
 */
import { getNotebookUrl, getNotebookFolderUrl } from "@/lib/api";
import { openInDatabricks } from "@/config/workspace";

/** Open a notebook in Databricks by ID. Uses GET /api/notebooks/notebooks/{id}/url. */
export async function openNotebookInDatabricks(notebookId: string): Promise<void> {
  try {
    const { data } = await getNotebookUrl(
      { notebook_id: notebookId },
      { credentials: "include" }
    );
    if (data?.url) openInDatabricks(data.url);
  } catch (error) {
    console.error("Failed to open notebook:", error);
  }
}

/** Open a folder in Databricks by ID. Uses GET /api/notebooks/notebooks/folders/{id}/url. */
export async function openFolderInDatabricks(folderId: string): Promise<void> {
  try {
    const { data } = await getNotebookFolderUrl(
      { folder_id: folderId },
      { credentials: "include" }
    );
    if (data?.url) openInDatabricks(data.url);
  } catch (error) {
    console.error("Failed to open folder:", error);
  }
}
