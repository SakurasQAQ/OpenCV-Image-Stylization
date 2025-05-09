document.addEventListener("DOMContentLoaded", function () {
    let currentMode = 'foreground';
    const maxForeground = 55;
    const maxBackground = 55;

    let foregroundPoints = [];
    let backgroundPoints = [];
    let boxPoints = [];
    let isBoxMode = false;

    let currentFilename = "";

    const img = document.getElementById("uploaded-image");
    const coords = document.getElementById("coords");
    const markerContainer = document.getElementById("marker-container");

    window.setMode = function (mode) {
        currentMode = mode;
        isBoxMode = (mode === 'box');

        const fgBtn = document.getElementById("foreground-btn");
        const bgBtn = document.getElementById("background-btn");
        const boxBtn = document.getElementById("box-btn");

        fgBtn.disabled = (mode === 'foreground');
        fgBtn.style.backgroundColor = (mode === 'foreground') ? 'var(--color-btn-cancel)' : 'var(--color-bt3)';

        bgBtn.disabled = (mode === 'background');
        bgBtn.style.backgroundColor = (mode === 'background') ? 'var(--color-btn-cancel)' : 'var(--color-bt3)';

        boxBtn.disabled = (mode === 'box');
        boxBtn.style.backgroundColor = (mode === 'box') ? 'var(--color-btn-cancel)' : 'var(--color-bt3)';
    };

    if (img && img.src) {
        const parts = img.src.split('/');
        currentFilename = parts[parts.length - 1];
        setMode('foreground');
    }

    if (img) {
        img.addEventListener("click", function (event) {
            const rect = img.getBoundingClientRect();
            const x = Math.round(event.clientX - rect.left);
            const y = Math.round(event.clientY - rect.top);

            // Box 模式逻辑
            if (isBoxMode) {
                if (boxPoints.length === 2) boxPoints = [];
                boxPoints.push({ x, y });
                drawBoxOverlay();
                return;
            }

            // 前景 / 背景点逻辑
            if (currentMode === 'foreground' && foregroundPoints.length >= maxForeground) {
                alert("The number of foreground points cannot exceed 5!");
                return;
            }
            if (currentMode === 'background' && backgroundPoints.length >= maxBackground) {
                alert("The number of background points cannot exceed 5!");
                return;
            }

            const marker = document.createElement("div");
            marker.classList.add("marker", currentMode);
            marker.style.left = `${x}px`;
            marker.style.top = `${y}px`;
            markerContainer.appendChild(marker);

            if (currentMode === 'foreground') {
                foregroundPoints.push({ x, y });
            } else if (currentMode === 'background') {
                backgroundPoints.push({ x, y });
            }

            updateCoordsDisplay();
        });
    }

    window.clearMarkers = function () {
        markerContainer.innerHTML = '';
        foregroundPoints = [];
        backgroundPoints = [];
        boxPoints = [];
        coords.textContent = 'Split Completed';
        alert("Clean all dots");

        setMode('foreground');
    };

    function drawBoxOverlay() {
        markerContainer.querySelectorAll(".box-overlay").forEach(e => e.remove());

        if (boxPoints.length === 2) {
            const x = Math.min(boxPoints[0].x, boxPoints[1].x);
            const y = Math.min(boxPoints[0].y, boxPoints[1].y);
            const width = Math.abs(boxPoints[1].x - boxPoints[0].x);
            const height = Math.abs(boxPoints[1].y - boxPoints[0].y);

            const box = document.createElement("div");
            box.className = "box-overlay";
            box.style.position = "absolute";
            box.style.left = `${x}px`;
            box.style.top = `${y}px`;
            box.style.width = `${width}px`;
            box.style.height = `${height}px`;
            box.style.border = "2px dashed green";
            markerContainer.appendChild(box);
        }

        updateCoordsDisplay();
    }

    function updateCoordsDisplay() {
        const fgCoords = foregroundPoints.map(p => `(${p.x}, ${p.y})`).join(', ');
        const bgCoords = backgroundPoints.map(p => `(${p.x}, ${p.y})`).join(', ');
        const boxText = (boxPoints.length === 2)
            ? `(${boxPoints[0].x}, ${boxPoints[0].y}) → (${boxPoints[1].x}, ${boxPoints[1].y})`
            : 'None';

        coords.innerHTML = `
            <div><strong>FrontPoints:</strong> ${fgCoords || 'None'}</div>
            <div><strong>BackPoints:</strong> ${bgCoords || 'None'}</div>
            <div><strong>Box:</strong> ${boxText}</div>
        `;
    }

    window.submitPoints = function () {
        if (foregroundPoints.length + backgroundPoints.length === 0 && boxPoints.length !== 2) {
            alert("Please mark at least one point or a box.");
            return;
        }

        const progress = document.getElementById("submit-progress");
        const progressBar = document.getElementById("progress-bar");

        progress.style.display = "block";
        progressBar.value = 30;

        setTimeout(() => {
            progressBar.value = 60;
        }, 1000);

        const origWidth = parseInt(document.getElementById("img-width").value);
        const origHeight = parseInt(document.getElementById("img-height").value);

        fetch("/getpoints", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                filename: currentFilename,
                foreground: foregroundPoints,
                background: backgroundPoints,
                box: (boxPoints.length === 2) ? boxPoints : null,
                original_size: { width: origWidth, height: origHeight }
            })
        })
        .then(res => res.json())
        .then(data => {
            alert("Submit succeed! Backend return: " + data.message);

            const container = document.getElementById("resultContainer");
            container.innerHTML = "";

            progressBar.value = 100;
            progress.style.display = "none";
            progressBar.value = 0;

            data.result.forEach((path, index) => {
                const wrapper = document.createElement("div");
                wrapper.classList.add("result-item");

                const label = document.createElement("div");
                label.textContent = "Result " + (index + 1);
                label.style.fontWeight = "bold";
                label.style.marginBottom = "5px";

                const img = document.createElement("img");
                img.src = path + "?t=" + Date.now();
                img.alt = "Result " + (index + 1);
                img.style.maxWidth = "100%";
                img.style.border = "1px solid #ccc";
                img.style.width = "400px";
                img.style.height = "auto";
                img.style.objectFit = "contain";

                wrapper.appendChild(label);
                wrapper.appendChild(img);
                container.appendChild(wrapper);
            });
            document.getElementById("selection-controls").style.display = "block";
        })
        .catch(err => {
            console.error("submit failed", err);
            alert("submit failed");
        });
    };

    window.confirmSelection = function () {
        const selected = document.querySelector('input[name="resultChoice"]:checked');
        if (!selected) {
            alert("Please select one result before confirming.");
            return;
        }

        const selectedIndex = selected.value;
        const selectedPath = `static/uploads/result_${currentFilename.split('.')[0]}_${selectedIndex}.png`;

        fetch("/confirm_result", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                filename: currentFilename,
                selected_result: selectedPath
            })
        })
        .then(res => res.json())
        .then(data => alert("Confirmed: " + data.message))
        .catch(err => console.error("Confirmation failed", err));
    };
});
