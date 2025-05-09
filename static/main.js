


document.addEventListener("DOMContentLoaded", function () {
    let currentMode = 'foreground';
    const maxForeground = 5;
    const maxBackground = 5;

    let foregroundPoints = [];
    let backgroundPoints = [];

    let currentFilename = "";

    const img = document.getElementById("uploaded-image");
    const coords = document.getElementById("coords");
    const markerContainer = document.getElementById("marker-container");




    window.setMode = function (mode) {
        currentMode = mode;

        const fgBtn = document.getElementById("foreground-btn");
        const bgBtn = document.getElementById("background-btn");

        if (mode === 'foreground') {
            fgBtn.disabled = true;
            fgBtn.style.backgroundColor = '#888';
            bgBtn.disabled = false;
            bgBtn.style.backgroundColor = 'var(--color-bt3)';
        } else {
            bgBtn.disabled = true;
            bgBtn.style.backgroundColor = '#888';
            fgBtn.disabled = false;
            fgBtn.style.backgroundColor = 'var(--color-bt3)';
        }
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


            if (currentMode === 'foreground' && foregroundPoints.length >= maxForeground) {
                alert("The number of foreground attractions cannot exceed 5!");
                return;
            }
            if (currentMode === 'background' && backgroundPoints.length >= maxBackground) {
                alert("The number of background attractions cannot exceed 5!");
                return;
            }

            const marker = document.createElement("div");
            marker.classList.add("marker", currentMode);
            marker.style.left = `${x}px`;
            marker.style.top = `${y}px`;
            markerContainer.appendChild(marker);

            if (currentMode === 'foreground') {
                foregroundPoints.push({ x, y });
            } else {
                backgroundPoints.push({ x, y });
            }

            const fgCoords = foregroundPoints.map(p => `(${p.x}, ${p.y})`).join(', ');
            const bgCoords = backgroundPoints.map(p => `(${p.x}, ${p.y})`).join(', ');

            coords.innerHTML = `
                <div><strong>FrontPoints:</strong> ${fgCoords || 'None'}</div>
                <div><strong>BackPoints:</strong> ${bgCoords || 'None'}</div>`;



        });
    }

    window.clearMarkers = function () {
        markerContainer.innerHTML = '';
        foregroundPoints = [];
        backgroundPoints = [];
        coords.textContent = '??';
        alert("Clean all dots");

        setMode('foreground');
    };

    

    // submit pots to backend
    window.submitPoints = function () {

        if (foregroundPoints.length + backgroundPoints.length === 0) {
            alert("Please tag at least one frontpoint!");
            return;
        }


        const progress = document.getElementById("submit-progress");
        const progressBar = document.getElementById("progress-bar");

        
        progress.style.display = "block";
        progressBar.value = 30; 


        setTimeout(() => {
            progressBar.value = 60; 
        }, 1000);

    
        fetch("/getpoints", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                filename: currentFilename,
                foreground: foregroundPoints,
                background: backgroundPoints
            })
        })
        .then(
            res => res.json())
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
            
        })
        .catch(err => {
            console.error("submit failed", err);
            alert("submit failed", err);
        });
    };
});
