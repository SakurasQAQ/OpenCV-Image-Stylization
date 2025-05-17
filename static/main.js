document.addEventListener("DOMContentLoaded", function () {
    let currentMode = 'foreground';
    let currentStylizeMode = 'foreground';
    const maxForeground = 55;
    const maxBackground = 55;


    let foregroundPoints = [];
    let backgroundPoints = [];

    let boxCssPoints = [];
    let boxPoints = [];

    let isBoxMode = false;
    let currentFilename = "";

    let scaleX = 1, scaleY = 1;

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
        fgBtn.style.backgroundColor = (mode === 'foreground')
            ? 'var(--color-btn-cancel)'
            : 'var(--color-bt3)';

        bgBtn.disabled = (mode === 'background');
        bgBtn.style.backgroundColor = (mode === 'background')
            ? 'var(--color-btn-cancel)'
            : 'var(--color-bt3)';

        boxBtn.disabled = (mode === 'box');
        boxBtn.style.backgroundColor = (mode === 'box')
            ? 'var(--color-btn-cancel)'
            : 'var(--color-bt3)';
    };


    if (img && img.src) {
        const parts = img.src.split('/');
        currentFilename = parts[parts.length - 1];
        setMode('foreground');
    }


    if (img) {
        img.addEventListener("load", () => {
            const dpr = window.devicePixelRatio || 1;
            scaleX = (img.naturalWidth  / img.clientWidth)  * dpr;
            scaleY = (img.naturalHeight / img.clientHeight) * dpr;
            console.log("scaleX, scaleY, DPR =", scaleX.toFixed(3), scaleY.toFixed(3), dpr);
          });
    }


    if (img) {
        img.addEventListener("click", function (event) {
            const rect = img.getBoundingClientRect();
            const x_img = event.clientX - rect.left;
            const y_img = event.clientY - rect.top;

            if (isBoxMode) {
                if (boxCssPoints.length === 2) {
                    boxCssPoints = [];
                    boxPoints    = [];
                }

                boxCssPoints.push({ x: x_img, y: y_img });
                const x_ori = Math.round(x_img * scaleX);
                const y_ori = Math.round(y_img * scaleY);
                boxPoints.push({ x: x_ori, y: y_ori });

                drawBoxOverlay();
                return;
            }

            if (currentMode === 'foreground' && foregroundPoints.length >= maxForeground) {
                alert(` ${maxForeground} is maximum foreground points`);
                return;
            }
            if (currentMode === 'background' && backgroundPoints.length >= maxBackground) {
                alert(` ${maxBackground} is maximum background points`);
                return;
            }


            const marker = document.createElement("div");
            marker.classList.add("marker", currentMode);
            marker.style.left = `${x_img}px`;
            marker.style.top  = `${y_img}px`;
            markerContainer.appendChild(marker);

            const x_ori = Math.round(x_img * scaleX);
            const y_ori = Math.round(y_img * scaleY);
            if (currentMode === 'foreground') {
                foregroundPoints.push({ x: x_ori, y: y_ori });
            } else {
                backgroundPoints.push({ x: x_ori, y: y_ori });
            }

            updateCoordsDisplay();
        });
    }


    window.clearMarkers = function () {
        markerContainer.innerHTML = '';
        foregroundPoints = [];
        backgroundPoints = [];
        boxCssPoints = [];
        boxPoints    = [];
        coords.textContent = 'Split Completed';
        alert("All marks cleared");
        setMode('foreground');
    };


    function drawBoxOverlay() {

        markerContainer.querySelectorAll(".box-overlay").forEach(el => el.remove());

        if (boxCssPoints.length === 2) {
            const x = Math.min(boxCssPoints[0].x, boxCssPoints[1].x);
            const y = Math.min(boxCssPoints[0].y, boxCssPoints[1].y);
            const w = Math.abs(boxCssPoints[1].x - boxCssPoints[0].x);
            const h = Math.abs(boxCssPoints[1].y - boxCssPoints[0].y);

            const box = document.createElement("div");
            box.className = "box-overlay";
            box.style.position = "absolute";
            box.style.left     = `${x}px`;
            box.style.top      = `${y}px`;
            box.style.width    = `${w}px`;
            box.style.height   = `${h}px`;
            box.style.border   = "2px dashed green";
            markerContainer.appendChild(box);
        }

        updateCoordsDisplay();
    }


    function updateCoordsDisplay() {
        const fgText = foregroundPoints.map(p => `(${p.x},${p.y})`).join(', ') || 'None';
        const bgText = backgroundPoints.map(p => `(${p.x},${p.y})`).join(', ') || 'None';
        const boxText = boxPoints.length === 2
            ? `(${boxPoints[0].x},${boxPoints[0].y}) → (${boxPoints[1].x},${boxPoints[1].y})`
            : 'None';

        coords.innerHTML = `
          <div><strong>FrontPoints:</strong> ${fgText}</div>
          <div><strong>BackPoints:</strong> ${bgText}</div>
          <div><strong>Box:</strong> ${boxText}</div>
        `;
    }


    window.submitPoints = function () {
        if (foregroundPoints.length + backgroundPoints.length === 0
            && boxPoints.length !== 2) {
            alert("Mark at least one point.");
            return;
        }

        const progress    = document.getElementById("submit-progress");
        const progressBar = document.getElementById("progress-bar");
        progress.style.display = "block";
        progressBar.value      = 30;

        setTimeout(() => progressBar.value = 60, 500);

        fetch("/getpoints", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                filename:   currentFilename,
                foreground: foregroundPoints,
                background: backgroundPoints,
                box:        (boxPoints.length === 2) ? boxPoints : null
            })
        })
        .then(res => res.json())
        .then(data => {
            alert("Submit successfully: " + data.message);
            renderResults(data.result);
            progressBar.value = 100;
            progress.style.display = "none";
            progressBar.value = 0;
            document.getElementById("selection-controls").style.display = "block";
            document.getElementById("segmentation-section").style.display = "block";
        })
        .catch(err => {
            console.error("submit failed", err);
            alert("Submission failed");
        });
    };

    function renderResults(resultPaths) {
        const container = document.getElementById("resultContainer");
        container.innerHTML = "";
        for (let i = 0; i < resultPaths.length; i += 2) {
            const wrapper = document.createElement("div");
            wrapper.classList.add("result-row");
            wrapper.style.display     = "flex";
            wrapper.style.gap         = "10px";
            wrapper.style.marginBottom= "20px";

            const label = document.createElement("div");
            label.textContent = `Result ${Math.floor(i/2)+1}`;
            label.style.fontWeight = "bold";
            label.style.textAlign  = "center";

            const col = document.createElement("div");
            col.style.display         = "flex";
            col.style.flexDirection   = "column";
            col.style.alignItems      = "center";
            col.style.width           = "100%";

            const img1 = document.createElement("img");
            img1.src   = resultPaths[i] + "?t=" + Date.now();
            img1.alt   = `Mask ${i}`; 
            img1.style.width    = "400px";
            img1.style.objectFit= "contain";

       
            const img2 = document.createElement("img");
            img2.src   = resultPaths[i+1] + "?t=" + Date.now();
            img2.alt   = `Inverted ${i}`; 
            img2.style.width    = "400px";
            img2.style.objectFit= "contain";

            col.appendChild(label);
            wrapper.appendChild(img1);
            wrapper.appendChild(img2);
            container.appendChild(wrapper);
        }
    }

    window.confirmSelection = function () {
    const sel = document.querySelector('input[name="resultChoice"]:checked');
    if (!sel) {
        alert("Please select a segmentation result first.");
        return;
    }
    const idx      = sel.value;
    const baseName = `result_${currentFilename.split('.')[0]}_${idx}`;
    const maskPath = `static/uploads/${baseName}_mask.png`;
    window.originalFileName  = currentFilename;
    window.selectedMaskPath  = maskPath;


    fetch("/confirm_result", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            filename:            currentFilename,
            selected_foreground: `static/uploads/${baseName}.png`,
            selected_background: `static/uploads/${baseName}_inverted.png`
        })
    })
    .then(res => res.json())
    .then(d => {
        
        document.getElementById("stylize-section").style.display = "block";  
    })
    .catch(err => console.error("Confirmation failed", err));
    }

    window.onRegionSelect = function() {
    document.getElementById("apply-stylization-btn").style.display = "inline-block";
    };

    window.applyStylization = function (style) {
    if (!window.selectedMaskPath || !window.originalFileName) {
        alert("Missing selected region or filename");
        return;
    }
    fetch('/stylize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
        filename: window.originalFileName,
        mask_path: window.selectedMaskPath,
        stylePart: currentStylizeMode,    
        style: style
        })
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById('segmentation-section').style.display = 'none';
        document.getElementById('styled-img').src = '/' + data.styled_path;
        document.getElementById("styled-output").style.display = "block";
    })
    .catch(err => {
        console.error(err);
        alert("Stylization error");
    });
};

    window.setStylizeMode = function(mode) {
        currentStylizeMode = mode;
        const fgBtn = document.getElementById('stylize-foreground-btn');
        const bgBtn = document.getElementById('stylize-background-btn');
        fgBtn.disabled = (mode === 'foreground');
        fgBtn.style.backgroundColor = mode === 'foreground'
            ? 'var(--color-btn-cancel)'
            : 'var(--color-bt3)';
        bgBtn.disabled = (mode === 'background');
        bgBtn.style.backgroundColor = mode === 'background'
            ? 'var(--color-btn-cancel)'
            : 'var(--color-bt3)';
        

        document.getElementById('stylize-go-btn').style.display = 'block';
        
        // document.getElementById('animegan-go-btnX').style.display = 'block';
        document.getElementById('stylize-sh-btn').style.display = 'block';
        document.getElementById('stylize-ho-btn').style.display = 'block';
        document.getElementById('stylize-pa-btn').style.display = 'block';
        };








//         window.applyAnimeGANStylization = function () {
//     if (!window.selectedMaskPath || !window.originalFileName) {
//         alert("Missing selected region or filename");
//         return;
//     }

//     fetch('/stylize', {
//         method: 'POST',
//         headers: { 'Content-Type': 'application/json' },
//         body: JSON.stringify({
//             filename: window.originalFileName,
//             mask_path: window.selectedMaskPath,
//             stylePart: currentStylizeMode,  // 和 Hayao Miyazaki 共用
//             style: 'animegan'
//         })
//     })
//     .then(res => res.json())
//     .then(data => {
//         document.getElementById('segmentation-section').style.display = 'none';
//         document.getElementById('styled-img').src = '/' + data.styled_path;
//         document.getElementById("styled-output").style.display = "block";
//     })
//     .catch(err => {
//         console.error(err);
//         alert("Stylization error");
//     });
// };

    




}); 
