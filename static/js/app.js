// static/js/app.js - v5: Complete, Consolidated Version

// --- 1. GLOBAL STATE & ELEMENT VARIABLES ---

// State Variables
let tasks = [];
let currentOpenTaskIdForModal = null;
let currentEditingTaskId = null;
let isEditMode = false;
// Note: currentProjectId and currentUserId are expected to be set by an inline script in the HTML template from Flask

// DOM Element Variables (declared globally, assigned in DOMContentLoaded)
let taskListElement, taskTitleInputElement, taskDescriptionInputElement, taskDueDateInputElement,
    taskPriorityInputElement, taskAssigneeInputElement, addTaskBtnElement, inputAreaElement,
    taskDetailsModal, modalTaskTitle, modalTaskDescription, modalTaskDueDate,
    modalTaskPriority, modalTaskAssignee, modalTaskStatus, modalEditTaskBtn,
    modalTaskCommentsList, modalNewCommentInput, modalAddCommentBtn,
    voiceListeningModal, mainFabElement, fabOptionsMenuElement,
    fabVoiceAddBtn, fabManualAddBtn;


// --- 2. GLOBAL HELPER & CORE LOGIC FUNCTIONS ---

/**
 * A helper function to make API requests to the Flask backend.
 * @param {string} endpoint - The API endpoint to call (e.g., '/api/tasks/1').
 * @param {string} method - The HTTP method (GET, POST, PUT, DELETE).
 * @param {object} body - The JSON body for POST/PUT requests.
 * @returns {Promise<any>} The JSON response from the server or null on error.
 */
async function apiRequest(endpoint, method = 'GET', body = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    if (body) {
        options.body = JSON.stringify(body);
    }
    try {
        const response = await fetch(endpoint, options);
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: "An unknown error occurred" }));
            console.error(`API Error (${response.status}):`, errorData);
            alert(`Error: ${errorData.error || response.statusText}`);
            return null;
        }
        if (response.status === 204 || (response.headers.get("content-length") || "0") === "0") {
            return true;
        }
        return await response.json();
    } catch (error) {
        console.error('Network or Fetch Error:', error);
        alert('Network error. Please check your connection or try again.');
        return null;
    }
}

/**
 * Renders the list of tasks to the DOM.
 */
function renderTasks() {
    if (!taskListElement) return;

    taskListElement.innerHTML = '';

    if (tasks.length === 0 && currentProjectId) {
        taskListElement.innerHTML = '<li>No tasks yet for this project. Add one!</li>';
        return;
    }

    tasks.forEach(task => {
        const listItem = document.createElement('li');
        listItem.classList.add('task-item');
        listItem.dataset.id = task.id;
        if (task.is_completed) {
            listItem.classList.add('completed');
        }

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = task.is_completed;
        checkbox.onchange = () => toggleTaskStatus(task.id);

        const taskContentDiv = document.createElement('div');
        taskContentDiv.classList.add('task-content');
        taskContentDiv.onclick = () => showTaskDetailsModal(task.id);

        const titleSpan = document.createElement('span');
        titleSpan.classList.add('task-title');
        titleSpan.textContent = task.title;
        taskContentDiv.appendChild(titleSpan);

        if (task.description) {
            const descriptionP = document.createElement('p');
            descriptionP.classList.add('task-description');
            descriptionP.textContent = task.description;
            taskContentDiv.appendChild(descriptionP);
        }

        const metaDiv = document.createElement('div');
        metaDiv.classList.add('task-meta');

        if (task.due_date) {
            const dueDateP = document.createElement('p');
            dueDateP.classList.add('task-duedate');
            const today = new Date().toISOString().split('T')[0];
            if (task.due_date < today && !task.is_completed) {
                dueDateP.classList.add('overdue');
            }
            dueDateP.textContent = `Due: ${task.due_date}`;
            metaDiv.appendChild(dueDateP);
        }

        if (task.priority) {
            const priorityP = document.createElement('p');
            priorityP.classList.add('task-priority-display');
            priorityP.innerHTML = `Priority: <span class="priority-tag priority-${task.priority}">${task.priority}</span>`;
            metaDiv.appendChild(priorityP);
        }

        if (task.assignee_name) {
            const assigneeP = document.createElement('p');
            assigneeP.classList.add('task-assignee');
            assigneeP.textContent = `Assigned to: ${task.assignee_name}`;
            metaDiv.appendChild(assigneeP);
        }

        taskContentDiv.appendChild(metaDiv);

        const deleteButton = document.createElement('button');
        deleteButton.textContent = 'Delete';
        deleteButton.classList.add('delete-btn');
        deleteButton.onclick = (event) => {
            event.stopPropagation();
            deleteTask(task.id);
        };

        listItem.appendChild(checkbox);
        listItem.appendChild(taskContentDiv);
        listItem.appendChild(deleteButton);

        taskListElement.appendChild(listItem);
    });
}

/**
 * Fetches all tasks for the current project from the API and renders them.
 */
async function fetchTasks() {
    if (!currentProjectId) { return; }
    const fetchedTasks = await apiRequest(`/api/project/${currentProjectId}/tasks`);
    if (fetchedTasks) {
        tasks = fetchedTasks;
        renderTasks();
    }
}

/**
 * Adds a new task via the API.
 */
async function addTask(title, description, dueDate, priority, assigneeId) {
    if (!currentProjectId || !title || title.trim() === "") {
        alert("Task title cannot be empty!"); return;
    }
    const newTaskData = {
        title: title.trim(),
        description: description.trim(),
        due_date: dueDate,
        priority: priority,
        assignee_id: assigneeId || currentUserId
    };
    const createdTask = await apiRequest(`/api/project/${currentProjectId}/tasks`, 'POST', newTaskData);
    if (createdTask) {
        await fetchTasks();
    }
}

/**
 * Toggles the completion status of a task via the API.
 */
async function toggleTaskStatus(taskId) {
    const updatedTask = await apiRequest(`/api/tasks/${taskId}/toggle_complete`, 'PUT');
    if (updatedTask) {
        await fetchTasks();
    }
}

/**
 * Deletes a task via the API.
 */
async function deleteTask(taskId) {
    if (confirm('Are you sure you want to delete this task?')) {
        const success = await apiRequest(`/api/tasks/${taskId}`, 'DELETE');
        if (success) {
            await fetchTasks();
        }
    }
}

/**
 * Fetches and renders comments for a specific task into the modal.
 */
async function fetchAndRenderComments(taskId) {
    if (!taskId || !modalTaskCommentsList) return;
    modalTaskCommentsList.innerHTML = '<li>Loading comments...</li>';
    const comments = await apiRequest(`/api/task/${taskId}/comments`);

    if (comments && Array.isArray(comments)) {
        modalTaskCommentsList.innerHTML = '';
        if (comments.length === 0) {
            modalTaskCommentsList.innerHTML = '<li>No comments yet for this task.</li>';
        } else {
            comments.forEach(comment => {
                const listItem = document.createElement('li');
                const metaSpan = document.createElement('div');
                metaSpan.classList.add('comment-meta');
                const date = new Date(comment.created_at);
                const formattedTimestamp = `${date.toLocaleDateString()} ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
                metaSpan.textContent = `${comment.user_name || 'Unknown User'} - ${formattedTimestamp}`;
                const textP = document.createElement('div');
                textP.classList.add('comment-text');
                textP.textContent = comment.comment_text;
                listItem.appendChild(metaSpan);
                listItem.appendChild(textP);
                modalTaskCommentsList.appendChild(listItem);
            });
        }
        modalTaskCommentsList.scrollTop = modalTaskCommentsList.scrollHeight;
    } else {
        modalTaskCommentsList.innerHTML = '<li>Could not load comments.</li>';
    }
}

/**
 * Handles the click of the 'Add Comment' button in the modal.
 */
async function handleAddNewComment() {
    if (!modalNewCommentInput || !currentOpenTaskIdForModal) return;
    const commentText = modalNewCommentInput.value.trim();
    if (commentText) {
        const commentData = { comment_text: commentText };
        modalAddCommentBtn.disabled = true;
        modalAddCommentBtn.textContent = 'Posting...';
        const newComment = await apiRequest(`/api/task/${currentOpenTaskIdForModal}/comments`, 'POST', commentData);
        modalAddCommentBtn.disabled = false;
        modalAddCommentBtn.textContent = 'Add Comment';
        if (newComment && newComment.id) {
            await fetchAndRenderComments(currentOpenTaskIdForModal);
            modalNewCommentInput.value = '';
            modalNewCommentInput.focus();
        } else {
            alert("Failed to add comment. Please try again.");
        }
    } else {
        alert("Comment cannot be empty.");
    }
}

/**
 * Shows and populates the Task Details modal.
 */
function showTaskDetailsModal(taskId) {
    currentOpenTaskIdForModal = taskId;
    const task = tasks.find(t => t.id === taskId);
    if (task && modalTaskTitle) {
        modalTaskTitle.textContent = task.title;
        modalTaskDescription.textContent = task.description || 'N/A';
        modalTaskDueDate.textContent = task.due_date || 'N/A';
        modalTaskPriority.textContent = task.priority || 'N/A';
        modalTaskAssignee.textContent = task.assignee_name || 'N/A';
        modalTaskStatus.textContent = task.is_completed ? 'Completed' : 'Pending';
        if (modalNewCommentInput) modalNewCommentInput.value = '';
        fetchAndRenderComments(taskId);
        taskDetailsModal.style.display = 'block';
    } else {
        console.error("Task not found or modal elements not ready for taskId:", taskId);
    }
}

/**
 * Closes the Task Details modal.
 */
function closeTaskDetailsModal() { if (taskDetailsModal) taskDetailsModal.style.display = 'none'; currentOpenTaskIdForModal = null; }

/**
 * Puts the UI into 'edit mode' for a specific task.
 */
function initiateEditTask() {
    if (!currentOpenTaskIdForModal || !taskTitleInputElement) return;
    const taskToEdit = tasks.find(t => t.id === currentOpenTaskIdForModal);
    if (!taskToEdit) { alert("Error: Task to edit not found."); return; }
    isEditMode = true;
    currentEditingTaskId = taskToEdit.id;
    taskTitleInputElement.value = taskToEdit.title;
    taskDescriptionInputElement.value = taskToEdit.description || '';
    taskDueDateInputElement.value = taskToEdit.due_date || '';
    taskPriorityInputElement.value = taskToEdit.priority || 'Medium';
    taskAssigneeInputElement.value = taskToEdit.assignee_id || '';
    if (addTaskBtnElement) addTaskBtnElement.textContent = 'Save Changes';
    closeTaskDetailsModal();
    if (inputAreaElement) {
        inputAreaElement.style.display = 'block';
        inputAreaElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    if (taskTitleInputElement) setTimeout(() => { taskTitleInputElement.focus(); }, 300);
}

/**
 * Resets the task form back to 'Add Task' mode.
 */
function resetTaskForm() {
    if (!taskTitleInputElement || !addTaskBtnElement) return;
    isEditMode = false;
    currentEditingTaskId = null;
    taskTitleInputElement.value = '';
    taskDescriptionInputElement.value = '';
    taskDueDateInputElement.value = '';
    taskPriorityInputElement.value = 'Medium';
    taskAssigneeInputElement.value = '';

    addTaskBtnElement.textContent = 'Add Task';
    if (inputAreaElement) inputAreaElement.style.display = 'none';
}

/**
 * Shows the voice listening modal.
 */
function showVoiceListeningModal() { if (voiceListeningModal) voiceListeningModal.style.display = 'block'; }
/**
 * Closes the voice listening modal.
 */
function closeVoiceListeningModal() { if (voiceListeningModal) voiceListeningModal.style.display = 'none'; }
/**
 * Parses details from simulated voice input text.
 */
function parseTaskDetailsFromText(text) {
    let lowerText = text.toLowerCase();
    let dueDate = null;
    let priority = "Medium";
    let title = text;
    const datePatterns = { "due tomorrow": () => { const d = new Date(); d.setDate(d.getDate() + 1); return d; }, "due next week": () => { const d = new Date(); d.setDate(d.getDate() + 7); return d; }, "due next friday": () => { let d = new Date(); d.setDate(d.getDate() + (5 + 7 - d.getDay()) % 7); if (d <= new Date()) d.setDate(d.getDate() + 7); return d; } };
    for (const pattern in datePatterns) { if (lowerText.includes(pattern)) { const dateObj = datePatterns[pattern](); dueDate = dateObj.toISOString().split('T')[0]; title = title.replace(new RegExp(pattern, "gi"), "").trim(); lowerText = title.toLowerCase(); break; } }
    const priorityPatterns = { "high priority": "High", "priority high": "High", "low priority": "Low", "priority low": "Low" };
    for (const pattern in priorityPatterns) { if (lowerText.includes(pattern)) { priority = priorityPatterns[pattern]; title = title.replace(new RegExp(pattern, "gi"), "").trim(); lowerText = title.toLowerCase(); break; } }
    return { title: title.trim(), description: "", dueDate, priority };
}


// --- 3. DOMContentLoaded EVENT LISTENER ---
// The main entry point after the HTML page is fully loaded.
document.addEventListener('DOMContentLoaded', () => {

    // Initialize all globally declared DOM element variables
    taskListElement = document.getElementById('taskList');
    taskTitleInputElement = document.getElementById('taskTitleInput');
    taskDescriptionInputElement = document.getElementById('taskDescriptionInput');
    taskDueDateInputElement = document.getElementById('taskDueDateInput');
    taskPriorityInputElement = document.getElementById('taskPriorityInput');
    taskAssigneeInputElement = document.getElementById('taskAssigneeInput');
    addTaskBtnElement = document.getElementById('addTaskBtn');
    inputAreaElement = document.querySelector('.input-area');
    taskDetailsModal = document.getElementById('taskDetailsModal');
    modalTaskTitle = document.getElementById('modalTaskTitle');
    modalTaskDescription = document.getElementById('modalTaskDescription');
    modalTaskDueDate = document.getElementById('modalTaskDueDate');
    modalTaskPriority = document.getElementById('modalTaskPriority');
    modalTaskAssignee = document.getElementById('modalTaskAssignee');
    modalTaskStatus = document.getElementById('modalTaskStatus');
    modalEditTaskBtn = document.getElementById('modalEditTaskBtn');
    modalTaskCommentsList = document.getElementById('modalTaskCommentsList');
    modalNewCommentInput = document.getElementById('modalNewCommentInput');
    modalAddCommentBtn = document.getElementById('modalAddCommentBtn');
    voiceListeningModal = document.getElementById('voiceListeningModal');
    mainFabElement = document.getElementById('mainFab');
    fabOptionsMenuElement = document.getElementById('fabOptionsMenu');
    fabVoiceAddBtn = document.getElementById('fabVoiceAdd');
    fabManualAddBtn = document.getElementById('fabManualAdd');

    // Attach Event Listeners
    if (addTaskBtnElement) {
        addTaskBtnElement.addEventListener('click', async () => {
            const title = taskTitleInputElement.value;
            const description = taskDescriptionInputElement.value;
            const dueDate = taskDueDateInputElement.value;
            const priority = taskPriorityInputElement.value;
            const assigneeId = taskAssigneeInputElement.value;
            if (isEditMode && currentEditingTaskId) {
                const updatedTaskData = { title: title.trim(), description: description.trim(), due_date: dueDate, priority: priority, assignee_id: assigneeId || null };
                const updatedTask = await apiRequest(`/api/tasks/${currentEditingTaskId}`, 'PUT', updatedTaskData);
                if (updatedTask) { await fetchTasks(); resetTaskForm(); }
            } else {
                await addTask(title, description, dueDate, priority, assigneeId);
                resetTaskForm();
            }
        });
    }

    if (modalEditTaskBtn) { modalEditTaskBtn.addEventListener('click', initiateEditTask); }
    if (modalAddCommentBtn) { modalAddCommentBtn.addEventListener('click', handleAddNewComment); }

    if (mainFabElement && fabOptionsMenuElement) {
        mainFabElement.addEventListener('click', () => { fabOptionsMenuElement.classList.toggle('hidden'); });
    }
    if (fabManualAddBtn) {
        fabManualAddBtn.addEventListener('click', () => {
            if (inputAreaElement) {
                if(isEditMode) resetTaskForm(); // If in edit mode, reset to 'Add' mode
                inputAreaElement.style.display = 'block';
                inputAreaElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                setTimeout(() => { taskTitleInputElement.focus(); }, 100);
            }
            if (fabOptionsMenuElement) fabOptionsMenuElement.classList.add('hidden');
        });
    }
    if (fabVoiceAddBtn) {
        fabVoiceAddBtn.addEventListener('click', () => {
            if (fabOptionsMenuElement) fabOptionsMenuElement.classList.add('hidden');
            showVoiceListeningModal();
            setTimeout(() => {
                const spokenText = prompt("SIMULATED VOICE INPUT:\nType your task details (e.g., 'Inspect south fence due tomorrow high priority'):", "");
                closeVoiceListeningModal();
                if (spokenText && spokenText.trim() !== "") {
                    const parsedDetails = parseTaskDetailsFromText(spokenText);
                    if (isEditMode) resetTaskForm(); // Reset form if in edit mode
                    taskTitleInputElement.value = parsedDetails.title;
                    taskDescriptionInputElement.value = parsedDetails.description;
                    if (parsedDetails.dueDate) taskDueDateInputElement.value = parsedDetails.dueDate;
                    taskPriorityInputElement.value = parsedDetails.priority;
                    taskAssigneeInputElement.value = '';
                    if (inputAreaElement) {
                        inputAreaElement.style.display = 'block';
                        inputAreaElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                    }
                    if (taskTitleInputElement) setTimeout(() => { taskTitleInputElement.focus(); }, 300);
                    alert("Task details pre-filled from 'voice' input. Please review, select an assignee if needed, and click 'Add Task'.");
                } else {
                    alert("Voice input cancelled or empty.");
                }
            }, 100);
        });
    }

    window.onclick = function(event) {
        if (event.target == taskDetailsModal) closeTaskDetailsModal();
        if (event.target == voiceListeningModal) closeVoiceListeningModal();
    };

    document.addEventListener('click', function(event) {
        if (mainFabElement && fabOptionsMenuElement && !mainFabElement.contains(event.target) && !fabOptionsMenuElement.contains(event.target)) {
            fabOptionsMenuElement.classList.add('hidden');
        }
    });

    // Initial data fetch
    if (typeof currentProjectId !== 'undefined' && currentProjectId) {
       fetchTasks();
    } else {
        if (document.querySelector('.container')) {
             document.querySelector('.container').innerHTML = "<h1>Error</h1><p>Project context not loaded. Please go back and select a user and project.</p><a href='/'>Start Over</a>";
        }
    }
});