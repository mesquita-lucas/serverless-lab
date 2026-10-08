let workspaceId = null;
let socket = null;

const elements = {
    workspaceId: document.getElementById("workspace-id"),
    connectionStatus: document.getElementById("connection-status"),
    queueState: document.getElementById("queue-state"),
    functionsState: document.getElementById("functions-state"),
    processedState: document.getElementById("processed-state"),
    architectureQueue: document.getElementById("architecture-queue"),
    architectureFunctions: document.getElementById("architecture-functions"),
    metricRequests: document.getElementById("metric-requests"),
    metricQueue: document.getElementById("metric-queue"),
    metricProcessed: document.getElementById("metric-processed"),
    metricFunctions: document.getElementById("metric-functions"),
    metricColdStarts: document.getElementById("metric-cold-starts"),
    metricLatency: document.getElementById("metric-latency"),
    functionGrid: document.getElementById("function-grid"),
    logsContainer: document.getElementById("logs-container"),
    customAmount: document.getElementById("custom-amount"),
    simulateCustom: document.getElementById("simulate-custom"),
    clearLogs: document.getElementById("clear-logs")
};

async function createWorkspace() {
    try {
        const response = await fetch("/api/workspaces", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            }
        });

        if (!response.ok) {
            throw new Error("Não foi possível criar o workspace.");
        }

        const data = await response.json();

        workspaceId = data.workspace_id || data.id;

        elements.workspaceId.textContent = workspaceId;

        connectWebSocket();
    } catch (error) {
        elements.workspaceId.textContent = "Erro";
        addLog("ERROR", error.message);
    }
}

function connectWebSocket() {
    if (!workspaceId) {
        return;
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    socket = new WebSocket(
        `${protocol}//${window.location.host}/ws/${workspaceId}`
    );

    socket.onopen = () => {
        elements.connectionStatus.classList.remove("offline");
        elements.connectionStatus.classList.add("online");
        elements.connectionStatus.innerHTML = "<span></span> Online";
    };

    socket.onclose = () => {
        elements.connectionStatus.classList.remove("online");
        elements.connectionStatus.classList.add("offline");
        elements.connectionStatus.innerHTML = "<span></span> Offline";

        setTimeout(connectWebSocket, 2000);
    };

    socket.onerror = () => {
        elements.connectionStatus.classList.remove("online");
        elements.connectionStatus.classList.add("offline");
        elements.connectionStatus.innerHTML = "<span></span> Offline";
    };

    socket.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleSocketMessage(data);
        } catch {
            addLog("EVENT", event.data);
        }
    };
}

function handleSocketMessage(data) {
    if (data.type === "metrics") {
        updateMetrics(data);
        return;
    }

    if (data.type === "log") {
        addLog(data.event || "EVENT", data.message || "");
        return;
    }

    if (data.type === "state") {
        updateMetrics(data);
        return;
    }

    if (data.metrics) {
        updateMetrics(data.metrics);
    }

    if (data.event || data.message) {
        addLog(data.event || "EVENT", data.message || "");
    }

    if (data.instances) {
        renderFunctions(data.instances);
    }

    if (Array.isArray(data.logs)) {
        renderLogs(data.logs);
    }
}

function renderLogs(logs) {
    elements.logsContainer.innerHTML = "";

    if (!logs.length) {
        elements.logsContainer.innerHTML = `
            <div class="log-empty">
                Aguardando eventos...
            </div>
        `;
        return;
    }

    logs
        .slice()
        .reverse()
        .forEach((log) => {
            addLog(
                log.event || "EVENT",
                JSON.stringify(log.data || {})
            );
        });
}

function updateMetrics(data) {
    const requests = valueFrom(data, ["requests", "total_requests"], 0);
    const queue = valueFrom(data, ["queued", "queue", "queue_size"], 0);
    const processed = valueFrom(data, ["processed", "processed_requests"], 0);
    const functions = valueFrom(data, ["active_instances", "functions", "function_count"], 0);
    const coldStarts = valueFrom(data, ["cold_starts", "cold_start_count"], 0);
    const latency = valueFrom(data, ["latency", "latency_ms"], 0);

    elements.queueState.textContent = queue;
    elements.functionsState.textContent = functions;
    elements.processedState.textContent = processed;

    elements.architectureQueue.textContent = `${queue} eventos`;
    elements.architectureFunctions.textContent = `${functions} ativas`;

    elements.metricRequests.textContent = requests;
    elements.metricQueue.textContent = queue;
    elements.metricProcessed.textContent = processed;
    elements.metricFunctions.textContent = functions;
    elements.metricColdStarts.textContent = coldStarts;
    elements.metricLatency.textContent = `${latency} ms`;

    if (data.functions) {
        renderFunctions(data.functions);
    }
}

function valueFrom(data, keys, fallback) {
    for (const key of keys) {
        if (data[key] !== undefined && data[key] !== null) {
            return data[key];
        }
    }

    return fallback;
}

async function simulate(amount) {
    if (!workspaceId) {
        addLog("ERROR", "Workspace ainda não está pronto.");
        return;
    }

    try {
        const response = await fetch("/api/simulate", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                workspace_id: workspaceId,
                amount: Number(amount)
            })
        });

        if (!response.ok) {
            throw new Error("Falha ao iniciar a simulação.");
        }

        addLog("SIMULATION", `${amount} pedidos adicionados à carga.`);
    } catch (error) {
        addLog("ERROR", error.message);
    }
}

function renderFunctions(functions) {
    if (!Array.isArray(functions) || functions.length === 0) {
        elements.functionGrid.innerHTML = `
            <div class="empty-state">
                Nenhuma Function ativa
            </div>
        `;
        return;
    }

    elements.functionGrid.innerHTML = "";

    functions.forEach((fn, index) => {
        const id = fn.id || fn.function_id || `F${index + 1}`;
        const state = String(fn.state || fn.status || "warm").toLowerCase();

        const instance = document.createElement("div");
        instance.className = `function-instance ${state}`;

        instance.innerHTML = `
            <div class="function-instance-header">
                <strong>${escapeHtml(id)}</strong>
                <span class="function-state">${escapeHtml(state)}</span>
            </div>
        `;

        elements.functionGrid.appendChild(instance);
    });
}

function addLog(type, message) {
    const empty = elements.logsContainer.querySelector(".log-empty");

    if (empty) {
        empty.remove();
    }

    const entry = document.createElement("div");
    entry.className = "log-entry";

    const time = new Date().toLocaleTimeString("pt-BR", {
        hour12: false
    });

    entry.innerHTML = `
        <span class="log-time">${time}</span>
        <span class="log-type">${escapeHtml(type)}</span>
        <span class="log-message">${escapeHtml(message)}</span>
    `;

    elements.logsContainer.prepend(entry);

    while (elements.logsContainer.children.length > 100) {
        elements.logsContainer.removeChild(elements.logsContainer.lastChild);
    }
}

function escapeHtml(value) {
    const element = document.createElement("div");
    element.textContent = String(value);
    return element.innerHTML;
}

document.querySelectorAll(".load-button").forEach((button) => {
    button.addEventListener("click", () => {
        simulate(button.dataset.amount);
    });
});

elements.simulateCustom.addEventListener("click", () => {
    const amount = Number(elements.customAmount.value);

    if (!amount || amount < 1) {
        addLog("ERROR", "Informe uma quantidade válida.");
        return;
    }

    simulate(amount);
});

elements.clearLogs.addEventListener("click", () => {
    elements.logsContainer.innerHTML = `
        <div class="log-empty">
            Aguardando eventos...
        </div>
    `;
});

createWorkspace();