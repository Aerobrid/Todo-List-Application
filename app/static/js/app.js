/**
 * Core Application Controller.
 * Manages runtime state, event bindings, and DOM manipulations.
 */
document.addEventListener("DOMContentLoaded", () => {
    // --- STATE MANAGER ---
    const state = {
        tasks: [],
        currentFilter: "all",
        searchQuery: "",
        sortBy: "created_desc",
        editingTaskId: null,
        hasAIKey: false
    };

    // Priority hierarchy maps enums to integer ranks for sorting routines
    const PRIORITY_RANKS = {
        "high": 3,
        "medium": 2,
        "low": 1
    };

    // --- DOM CACHE ---
    const DOM = {
        themeToggle: document.getElementById("theme-toggle"),
        taskForm: document.getElementById("task-form"),
        taskIdField: document.getElementById("task-id-field"),
        taskTitleInput: document.getElementById("task-title"),
        taskDescInput: document.getElementById("task-desc"),
        taskPrioritySelect: document.getElementById("task-priority"),
        taskCategorySelect: document.getElementById("task-category"),
        taskDueDateInput: document.getElementById("task-due-date"),
        formSubmitBtn: document.getElementById("form-submit-btn"),
        formCancelBtn: document.getElementById("form-cancel-btn"),

        
        searchInput: document.getElementById("search-input"),
        filterTabs: document.querySelectorAll(".filter-tab"),
        sortSelect: document.getElementById("sort-select"),
        statsCounter: document.getElementById("stats-counter"),
        clearCompletedBtn: document.getElementById("clear-completed-btn"),
        tasksContainer: document.getElementById("tasks-container"),
        alertBanner: document.getElementById("alert-banner"),
        
        customCategoryGroup: document.getElementById("custom-category-group"),
        taskCustomCategoryInput: document.getElementById("task-custom-category"),
        addTimeCheckbox: document.getElementById("add-time-checkbox"),
        taskDueTimeInput: document.getElementById("task-due-time")
    };

    // --- INITIALIZATION ---
    async function init() {
        setupTheme();
        bindEvents();
        await checkAIConfig();
        loadTasks();
    }

    // --- THEME SETUP ---
    function setupTheme() {
        const savedTheme = localStorage.getItem("theme") || "light";
        document.documentElement.setAttribute("data-theme", savedTheme);
        DOM.themeToggle.textContent = savedTheme === "dark" ? "Toggle Light Mode" : "Toggle Dark Mode";
    }

    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute("data-theme");
        const newTheme = currentTheme === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", newTheme);
        localStorage.setItem("theme", newTheme);
        DOM.themeToggle.textContent = newTheme === "dark" ? "Toggle Light Mode" : "Toggle Dark Mode";
    }

    // --- EVENT ROUTING ---
    function bindEvents() {
        DOM.themeToggle.addEventListener("click", toggleTheme);
        DOM.taskForm.addEventListener("submit", handleFormSubmit);
        DOM.formCancelBtn.addEventListener("click", handleCancelEdit);
        
        // Toggle Custom Category inputs
        DOM.taskCategorySelect.addEventListener("change", (e) => {
            if (e.target.value === "custom") {
                DOM.customCategoryGroup.classList.remove("hidden");
                DOM.taskCustomCategoryInput.required = true;
                DOM.taskCustomCategoryInput.focus();
            } else {
                DOM.customCategoryGroup.classList.add("hidden");
                DOM.taskCustomCategoryInput.required = false;
                DOM.taskCustomCategoryInput.value = "";
            }
        });

        // Toggle due time inputs
        DOM.addTimeCheckbox.addEventListener("change", (e) => {
            if (e.target.checked) {
                DOM.taskDueTimeInput.classList.remove("hidden");
                DOM.taskDueTimeInput.focus();
            } else {
                DOM.taskDueTimeInput.classList.add("hidden");
                DOM.taskDueTimeInput.value = "";
            }
        });
        
        // De-bounced search prevents excessive API calls while the user types
        let searchTimeout;
        DOM.searchInput.addEventListener("input", (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                state.searchQuery = e.target.value;
                loadTasks();
            }, 300);
        });

        // Register filter tabs
        DOM.filterTabs.forEach(tab => {
            tab.addEventListener("click", (e) => {
                DOM.filterTabs.forEach(t => t.classList.remove("active"));
                e.target.classList.add("active");
                state.currentFilter = e.target.dataset.filter;
                loadTasks();
            });
        });

        DOM.sortSelect.addEventListener("change", (e) => {
            state.sortBy = e.target.value;
            renderTasks();
        });

        DOM.clearCompletedBtn.addEventListener("click", handleClearCompleted);
        
        // Event delegation handles dynamic subtask checks, deletions, and additions
        DOM.tasksContainer.addEventListener("click", handleBoardInteraction);
    }

    // --- CORE DATA ACTIONS ---
    
    async function loadTasks() {
        try {
            // map filter tabs to backend boolean values
            let completedFilter = null;
            if (state.currentFilter === "active") completedFilter = false;
            if (state.currentFilter === "completed") completedFilter = true;

            state.tasks = await API.fetchTasks(completedFilter, state.searchQuery);
            renderTasks();
        } catch (error) {
            showAlert(error.message, "error");
        }
    }

    async function handleFormSubmit(e) {
        e.preventDefault();
        
        const title = DOM.taskTitleInput.value.trim();
        const description = DOM.taskDescInput.value.trim() || null;
        const priority = DOM.taskPrioritySelect.value;
        
        // Read either predefined category or custom text input value
        const categoryVal = DOM.taskCategorySelect.value;
        const category = categoryVal === "custom"
            ? (DOM.taskCustomCategoryInput.value.trim().toLowerCase() || "other")
            : categoryVal;

        // Merge date and optional time inputs, protecting against time drift
        let dueDate = null;
        if (DOM.taskDueDateInput.value) {
            if (DOM.addTimeCheckbox.checked && DOM.taskDueTimeInput.value) {
                dueDate = new Date(DOM.taskDueDateInput.value + "T" + DOM.taskDueTimeInput.value).toISOString();
            } else {
                dueDate = new Date(DOM.taskDueDateInput.value + "T12:00:00Z").toISOString();
            }
        }

        if (!title) {
            showAlert("Task title is required.", "error");
            return;
        }

        try {
            if (state.editingTaskId) {
                // UPDATE action
                await API.updateTask(state.editingTaskId, {
                    title,
                    description,
                    priority,
                    category,
                    due_date: dueDate
                });
                showAlert("Task updated successfully.", "success");
                handleCancelEdit(); // reset form fields
            } else {
                // CREATE action
                await API.createTask({
                    title,
                    description,
                    priority,
                    category,
                    due_date: dueDate
                });
                showAlert("Task created successfully.", "success");
                resetForm();
            }
            loadTasks();
        } catch (error) {
            showAlert(error.message, "error");
        }
    }


    async function handleClearCompleted() {
        try {
            const result = await API.clearCompleted();
            showAlert(`Cleared completed tasks. Rows removed: ${result.count}`, "success");
            loadTasks();
        } catch (error) {
            showAlert(error.message, "error");
        }
    }

    async function handleBoardInteraction(e) {
        const target = e.target;
        
        // 1. Task Checkbox toggle
        if (target.classList.contains("task-checkbox")) {
            const taskId = parseInt(target.dataset.id);
            const isCompleted = target.checked;
            try {
                await API.updateTask(taskId, { is_completed: isCompleted });
                loadTasks();
            } catch (error) {
                target.checked = !isCompleted; // rollback UI status
                showAlert(error.message, "error");
            }
            return;
        }

        // 2. Task Delete button
        if (target.classList.contains("action-delete-task")) {
            const taskId = parseInt(target.dataset.id);
            if (!confirm("Are you sure you want to delete this task?")) return;
            try {
                await API.deleteTask(taskId);
                showAlert("Task deleted.", "success");
                loadTasks();
            } catch (error) {
                showAlert(error.message, "error");
            }
            return;
        }

        // 3. Task Edit trigger
        if (target.classList.contains("action-edit-task")) {
            const taskId = parseInt(target.dataset.id);
            const task = state.tasks.find(t => t.id === taskId);
            if (task) {
                setupEditMode(task);
            }
            return;
        }

        // 4. Task AI Subtask Generator
        if (target.classList.contains("action-decompose-task")) {
            const taskId = parseInt(target.dataset.id);
            const task = state.tasks.find(t => t.id === taskId);
            if (!task) return;
            
            target.disabled = true;
            target.textContent = "Generating...";
            try {
                const result = await API.generateSubtasks(task.title, task.category, task.description);
                
                // add subtasks sequentially in DB
                for (const subTitle of result.subtasks) {
                    await API.addSubtask(taskId, { title: subTitle });
                }
                showAlert("Subtask suggestions generated successfully.", "success");
                loadTasks();
            } catch (error) {
                showAlert(error.message, "error");
            } finally {
                target.disabled = false;
                target.textContent = "Generate Subtasks";
            }
            return;
        }

        // 5. Subtask Checkbox toggle
        if (target.classList.contains("subtask-checkbox")) {
            const subId = parseInt(target.dataset.id);
            const isCompleted = target.checked;
            try {
                await API.toggleSubtask(subId, isCompleted);
                loadTasks();
            } catch (error) {
                target.checked = !isCompleted;
                showAlert(error.message, "error");
            }
            return;
        }

        // 6. Subtask Delete button
        if (target.classList.contains("btn-delete-subtask")) {
            const subId = parseInt(target.dataset.id);
            try {
                await API.deleteSubtask(subId);
                loadTasks();
            } catch (error) {
                showAlert(error.message, "error");
            }
            return;
        }

        // 7. Subtask Add Form submission
        if (target.classList.contains("btn-add-subtask")) {
            const taskId = parseInt(target.dataset.taskId);
            const inputEl = document.getElementById(`subtask-input-${taskId}`);
            const title = inputEl.value.trim();
            
            if (!title) {
                showAlert("Subtask name cannot be blank.", "error");
                return;
            }
            
            try {
                await API.addSubtask(taskId, { title });
                inputEl.value = "";
                loadTasks();
            } catch (error) {
                showAlert(error.message, "error");
            }
            return;
        }
    }

    // --- UI RENDERING & SORTING ENGINE ---
    
    function renderTasks() {
        DOM.tasksContainer.innerHTML = "";
        
        // Apply client-side sorting algorithms
        const sortedTasks = [...state.tasks].sort((a, b) => {
            // guard clause: keep completed tasks at the bottom of lists at all times
            if (a.is_completed !== b.is_completed) {
                return a.is_completed ? 1 : -1;
            }
            
            switch (state.sortBy) {
                case "due_asc":
                    if (!a.due_date) return 1;
                    if (!b.due_date) return -1;
                    return new Date(a.due_date) - new Date(b.due_date);
                case "priority_desc":
                    const rankA = PRIORITY_RANKS[a.priority] || 0;
                    const rankB = PRIORITY_RANKS[b.priority] || 0;
                    if (rankA !== rankB) {
                        return rankB - rankA;
                    }
                    return new Date(b.created_at) - new Date(a.created_at);
                case "created_desc":
                default:
                    return new Date(b.created_at) - new Date(a.created_at);
            }
        });

        renderStats(sortedTasks);

        if (sortedTasks.length === 0) {
            DOM.tasksContainer.innerHTML = `<div class="card"><p style="text-align: center; color: var(--text-secondary);">No tasks found.</p></div>`;
            return;
        }

        sortedTasks.forEach(task => {
            const cardEl = createTaskCardElement(task);
            DOM.tasksContainer.appendChild(cardEl);
        });
    }

    function renderStats(taskList) {
        // compute remaining active tasks
        const remainingCount = taskList.filter(t => !t.is_completed).length;
        DOM.statsCounter.textContent = `${remainingCount} task${remainingCount === 1 ? "" : "s"} remaining`;
    }

    function createTaskCardElement(task) {
        const card = document.createElement("div");
        card.className = `task-card ${task.is_completed ? "completed" : ""}`;
        
        // determine if overdue (due date in past and task is active)
        let isOverdue = false;
        let dueDateFormatted = "";
        if (task.due_date) {
            const dueTime = new Date(task.due_date);
            const isDateOnly = dueTime.getUTCHours() === 12 && dueTime.getUTCMinutes() === 0 && dueTime.getUTCSeconds() === 0;
            
            if (isDateOnly) {
                dueDateFormatted = dueTime.toLocaleDateString(undefined, {
                    month: "short", day: "numeric", year: "numeric"
                });
                const today = new Date();
                today.setHours(0, 0, 0, 0);
                const checkTime = new Date(dueTime);
                checkTime.setHours(0, 0, 0, 0);
                if (checkTime < today && !task.is_completed) {
                    isOverdue = true;
                }
            } else {
                dueDateFormatted = dueTime.toLocaleString(undefined, {
                    month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit"
                });
                if (dueTime < new Date() && !task.is_completed) {
                    isOverdue = true;
                }
            }
        }

        // render nested subtasks
        const subtasksHTML = task.subtasks.map(sub => `
            <li class="subtask-item ${sub.is_completed ? "completed" : ""}">
                <div class="subtask-left">
                    <input type="checkbox" class="subtask-checkbox" data-id="${sub.id}" ${sub.is_completed ? "checked" : ""}>
                    <span class="subtask-title-text">${sub.title}</span>
                </div>
                <button type="button" class="btn btn-secondary btn-sm btn-delete-subtask" data-id="${sub.id}" style="padding: 1px 4px; font-size: 10px;">
                    &times;
                </button>
            </li>
        `).join("");

        card.innerHTML = `
            <div class="task-header">
                <div class="task-checkbox-wrapper">
                    <input type="checkbox" class="task-checkbox" data-id="${task.id}" ${task.is_completed ? "checked" : ""}>
                </div>
                <div class="task-info">
                    <h3 class="task-title-text">${task.title}</h3>
                    ${task.description ? `<p class="task-desc-text">${task.description}</p>` : ""}
                    
                    <div class="task-metadata">
                        <span class="badge badge-priority-${task.priority}">${task.priority}</span>
                        <span class="badge badge-${task.category}">${task.category}</span>
                        ${task.due_date ? `
                            <span class="due-indicator ${isOverdue ? "overdue" : ""}">
                                Due: ${dueDateFormatted} ${isOverdue ? "(Overdue)" : ""}
                            </span>
                        ` : ""}
                    </div>
                </div>
            </div>
            
            <div class="subtasks-section">
                <h4 class="subtasks-title">Subtasks (${task.subtasks.filter(s => s.is_completed).length}/${task.subtasks.length})</h4>
                <ul class="subtasks-list">
                    ${subtasksHTML || `<li style="font-size: 12px; color: var(--text-muted); list-style: none;">No subtasks added yet.</li>`}
                </ul>
                <div class="subtask-add-form">
                    <input type="text" id="subtask-input-${task.id}" class="form-input" style="font-size: 12px; padding: 4px 8px;" placeholder="Add subtask...">
                    <button type="button" class="btn btn-secondary btn-sm btn-add-subtask" data-task-id="${task.id}">Add</button>
                </div>
            </div>
            
            <div class="task-actions">
                ${state.hasAIKey ? `
                <button type="button" class="btn btn-secondary btn-sm action-decompose-task" data-id="${task.id}">
                    Generate Subtasks
                </button>
                ` : ""}
                <button type="button" class="btn btn-secondary btn-sm action-edit-task" data-id="${task.id}">
                    Edit
                </button>
                <button type="button" class="btn btn-danger btn-sm action-delete-task" data-id="${task.id}">
                    Delete
                </button>
            </div>
        `;
        
        return card;
    }

    // --- FORM ACTIONS ---

    function setupEditMode(task) {
        state.editingTaskId = task.id;
        DOM.taskIdField.value = task.id;
        
        // Populate category dropdown and custom inputs
        const standardCategories = ["work", "personal", "shopping", "other"];
        if (standardCategories.includes(task.category)) {
            DOM.taskCategorySelect.value = task.category;
            DOM.customCategoryGroup.classList.add("hidden");
            DOM.taskCustomCategoryInput.value = "";
        } else {
            DOM.taskCategorySelect.value = "custom";
            DOM.customCategoryGroup.classList.remove("hidden");
            DOM.taskCustomCategoryInput.value = task.category || "";
        }
        
        if (task.due_date) {
            const date = new Date(task.due_date);
            const isDateOnly = date.getUTCHours() === 12 && date.getUTCMinutes() === 0 && date.getUTCSeconds() === 0;
            
            if (isDateOnly) {
                DOM.taskDueDateInput.value = task.due_date.substring(0, 10);
                DOM.addTimeCheckbox.checked = false;
                DOM.taskDueTimeInput.classList.add("hidden");
                DOM.taskDueTimeInput.value = "";
            } else {
                const year = date.getFullYear();
                const month = String(date.getMonth() + 1).padStart(2, '0');
                const day = String(date.getDate()).padStart(2, '0');
                DOM.taskDueDateInput.value = `${year}-${month}-${day}`;
                
                const hours = String(date.getHours()).padStart(2, '0');
                const minutes = String(date.getMinutes()).padStart(2, '0');
                DOM.taskDueTimeInput.value = `${hours}:${minutes}`;
                
                DOM.addTimeCheckbox.checked = true;
                DOM.taskDueTimeInput.classList.remove("hidden");
            }
        } else {
            DOM.taskDueDateInput.value = "";
            DOM.addTimeCheckbox.checked = false;
            DOM.taskDueTimeInput.classList.add("hidden");
            DOM.taskDueTimeInput.value = "";
        }

        DOM.taskTitleInput.value = task.title;
        DOM.taskDescInput.value = task.description || "";
        DOM.taskPrioritySelect.value = task.priority;

        DOM.formSubmitBtn.textContent = "Update Task";
        DOM.formCancelBtn.classList.remove("hidden");
        
        // Scroll to addition form panel smoothly for mobile responsiveness
        DOM.taskForm.scrollIntoView({ behavior: "smooth" });
    }

    function handleCancelEdit() {
        state.editingTaskId = null;
        DOM.taskIdField.value = "";
        resetForm();
        DOM.formSubmitBtn.textContent = "Save Task";
        DOM.formCancelBtn.classList.add("hidden");
    }

    function resetForm() {
        DOM.taskForm.reset();
        DOM.taskIdField.value = "";
        DOM.customCategoryGroup.classList.add("hidden");
        DOM.taskCustomCategoryInput.value = "";
        DOM.taskCustomCategoryInput.required = false;
        DOM.addTimeCheckbox.checked = true;
        DOM.taskDueTimeInput.classList.remove("hidden");
        DOM.taskDueTimeInput.value = "";
    }

    // --- SYSTEM UTILITIES ---

    async function checkAIConfig() {
        try {
            const config = await API.checkAIConfig();
            state.hasAIKey = config.has_api_key;
        } catch (error) {
            console.error("Failed to check AI config:", error);
            state.hasAIKey = false;
        }
    }

    function showAlert(message, type = "success") {
        DOM.alertBanner.className = `alert alert-${type}`;
        DOM.alertBanner.textContent = message;
        DOM.alertBanner.classList.remove("hidden");
        
        // Automatically hide notification banner after 4 seconds
        setTimeout(() => {
            DOM.alertBanner.classList.add("hidden");
        }, 4000);
    }

    /**
     * Converts raw UTC ISO dates to YYYY-MM-DD date-only values.
     * Prevents timezone shifts by slicing the ISO template directly.
     */
    function formatDateTimeForInput(isoString) {
        if (!isoString) return "";
        return isoString.substring(0, 10);
    }

    // Launch UI
    init();
});
