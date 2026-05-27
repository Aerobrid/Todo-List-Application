/**
 * Centralized API client abstraction.
 * Encapsulates fetch HTTP calls, handles status codes, sanitizes query parameters,
 * and standardizes error responses.
 */
const API = {
    /**
     * Queries tasks from the backend.
     * @param {boolean|null} isCompleted - filter state
     * @param {string} search - filter query keyword
     * @returns {Promise<Array>} List of tasks
     */
    async fetchTasks(isCompleted = null, search = "") {
        let url = "/api/tasks/?";
        const params = [];
        
        if (isCompleted !== null) {
            params.push(`is_completed=${isCompleted}`);
        }
        if (search && search.trim()) {
            params.push(`search=${encodeURIComponent(search.trim())}`);
        }
        
        url += params.join("&");
        
        const response = await fetch(url);
        return this._handleResponse(response, "Failed to retrieve tasks.");
    },

    /**
     * Adds a new task to the database.
     * @param {Object} taskData
     */
    async createTask(taskData) {
        const response = await fetch("/api/tasks/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(taskData)
        });
        return this._handleResponse(response, "Failed to create task.");
    },

    /**
     * Updates fields on an existing task.
     * @param {number} taskId
     * @param {Object} taskData
     */
    async updateTask(taskId, taskData) {
        const response = await fetch(`/api/tasks/${taskId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(taskData)
        });
        return this._handleResponse(response, "Failed to update task.");
    },

    /**
     * Deletes a task by ID.
     * @param {number} taskId
     */
    async deleteTask(taskId) {
        const response = await fetch(`/api/tasks/${taskId}`, {
            method: "DELETE"
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({ detail: "Failed to delete task." }));
            throw new Error(err.detail || "Delete operation error.");
        }
        return true;
    },

    /**
     * Bulk deletes all completed tasks.
     */
    async clearCompleted() {
        const response = await fetch("/api/tasks/clear-completed", {
            method: "POST"
        });
        return this._handleResponse(response, "Failed to clear completed tasks.");
    },

    /**
     * Creates a child subtask.
     * @param {number} taskId
     * @param {Object} subtaskData
     */
    async addSubtask(taskId, subtaskData) {
        const response = await fetch(`/api/tasks/${taskId}/subtasks`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(subtaskData)
        });
        return this._handleResponse(response, "Failed to append subtask.");
    },

    /**
     * Toggles a subtask's completion status.
     * @param {number} subtaskId
     * @param {boolean} isCompleted
     */
    async toggleSubtask(subtaskId, isCompleted) {
        const response = await fetch(`/api/tasks/subtasks/${subtaskId}?is_completed=${isCompleted}`, {
            method: "PUT"
        });
        return this._handleResponse(response, "Failed to update subtask status.");
    },

    /**
     * Deletes a subtask by ID.
     * @param {number} subtaskId
     */
    async deleteSubtask(subtaskId) {
        const response = await fetch(`/api/tasks/subtasks/${subtaskId}`, {
            method: "DELETE"
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({ detail: "Failed to delete subtask." }));
            throw new Error(err.detail || "Delete subtask operation error.");
        }
        return true;
    },



    /**
     * Generates a subtasks decomposition checklist for a task.
     * @param {string} title
     * @param {string} category
     * @param {string} description
     */
    async generateSubtasks(title, category, description = "") {
        let url = `/api/ai/subtasks?title=${encodeURIComponent(title)}&category=${encodeURIComponent(category)}`;
        if (description && description.trim()) {
            url += `&description=${encodeURIComponent(description.trim())}`;
        }
        const response = await fetch(url);
        return this._handleResponse(response, "Failed to generate AI subtask suggestions.");
    },

    /**
     * Checks if the Gemini API key is configured on the backend.
     * @returns {Promise<Object>} Object containing has_api_key boolean
     */
    async checkAIConfig() {
        const response = await fetch("/api/ai/config");
        return this._handleResponse(response, "Failed to retrieve AI configuration status.");
    },

    /**
     * Helper to parse JSON and intercept HTTP failure boundaries.
     * @private
     */
    async _handleResponse(response, fallbackMsg) {
        if (!response.ok) {
            // attempt parsing error detail returned from FastAPI HTTPException
            const err = await response.json().catch(() => ({ detail: fallbackMsg }));
            throw new Error(err.detail || fallbackMsg);
        }
        return response.json();
    }
};
Object.freeze(API);
