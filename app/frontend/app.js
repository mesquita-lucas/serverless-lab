let workspaceId = null;
let socket = null;

async function initialize() {
    const response = await fetch("/api/workspaces", {
        method: "POST"
    });

    const data = await response.json();

    workspaceId = data.workspace_id;

    connectWebSocket();
}

async function simulate(amount) {
    await fetch("/api/simulate", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            workspace_id: workspaceId,
            amount: amount
        })
    });
}

function connectWebSocket() {
    const protocol =
        location.protocol === "https:" ? "wss" : "ws";

    socket = new WebSocket(
        `${protocol}://${location.host}/ws/${workspaceId}`
    );

    socket.onmessage = event => {
        const data = JSON.parse(event.data);

        renderMetrics(data.metrics);
        renderFunctions(data.instances);
        renderLogs(data.logs);
    };
}

function renderMetrics(metrics) {
    document.getElementById("requests").textContent =
        metrics.requests;

    document.getElementById("queued").textContent =
        metrics.queued;

    document.getElementById("processed").textContent =
        metrics.processed;

    document.getElementById("instances").textContent =
        metrics.active_instances;

    document.getElementById("cold-starts").textContent =
        metrics.cold_starts;
}

function renderFunctions(instances) {
    const container =
        document.getElementById("functions");

    container.innerHTML = "";

    instances.forEach(instance => {
        const element = document.createElement("div");

        element.className = "function";

        let status = "COLD";

        if (instance.warm) {
            status = instance.busy ? "BUSY" : "WARM";
        }

        element.textContent =
            `${instance.id.slice(0, 6)} · ${status}`;

        container.appendChild(element);
    });
}

function renderLogs(logs) {
    const container =
        document.getElementById("logs");

    container.innerHTML = logs
        .slice()
        .reverse()
        .map(log => {
            return `<div>${log.event}</div>`;
        })
        .join("");
}

initialize();