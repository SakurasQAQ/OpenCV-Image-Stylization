document.addEventListener("DOMContentLoaded", function () {
    // 当前模式：foreground/background/box
    let currentMode = 'foreground';
    const maxForeground = 55;
    const maxBackground = 55;

    // 前景、背景的原图坐标
    let foregroundPoints = [];
    let backgroundPoints = [];
    // 框选：CSS 显示用 & 原图坐标用
    let boxCssPoints = [];
    let boxPoints = [];

    let isBoxMode = false;
    let currentFilename = "";

    // 缩放比：页面上展示 → 原图像素
    let scaleX = 1, scaleY = 1;

    const img = document.getElementById("uploaded-image");
    const coords = document.getElementById("coords");
    const markerContainer = document.getElementById("marker-container");

    // 切换标注模式
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

    // 取文件名
    if (img && img.src) {
        const parts = img.src.split('/');
        currentFilename = parts[parts.length - 1];
        setMode('foreground');
    }

    // 图片加载后计算缩放比
    if (img) {
        img.addEventListener("load", () => {
            const dpr = window.devicePixelRatio || 1;
            scaleX = (img.naturalWidth  / img.clientWidth)  * dpr;
            scaleY = (img.naturalHeight / img.clientHeight) * dpr;
            console.log("scaleX, scaleY, DPR =", scaleX.toFixed(3), scaleY.toFixed(3), dpr);
          });
    }

    // 点击标注
    if (img) {
        img.addEventListener("click", function (event) {
            const rect = img.getBoundingClientRect();
            const x_img = event.clientX - rect.left;
            const y_img = event.clientY - rect.top;

            // 框选模式
            if (isBoxMode) {
                if (boxCssPoints.length === 2) {
                    boxCssPoints = [];
                    boxPoints    = [];
                }
                // CSS 位置
                boxCssPoints.push({ x: x_img, y: y_img });
                // 原图位置
                const x_ori = Math.round(x_img * scaleX);
                const y_ori = Math.round(y_img * scaleY);
                boxPoints.push({ x: x_ori, y: y_ori });

                drawBoxOverlay();
                return;
            }

            // 点模式：数量限制
            if (currentMode === 'foreground' && foregroundPoints.length >= maxForeground) {
                alert(`最多 ${maxForeground} 个前景点`);
                return;
            }
            if (currentMode === 'background' && backgroundPoints.length >= maxBackground) {
                alert(`最多 ${maxBackground} 个背景点`);
                return;
            }

            // 画小圆点（用 CSS 坐标）
            const marker = document.createElement("div");
            marker.classList.add("marker", currentMode);
            marker.style.left = `${x_img}px`;
            marker.style.top  = `${y_img}px`;
            markerContainer.appendChild(marker);

            // 存原图坐标
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

    // 清除所有标记
    window.clearMarkers = function () {
        markerContainer.innerHTML = '';
        foregroundPoints = [];
        backgroundPoints = [];
        boxCssPoints = [];
        boxPoints    = [];
        coords.textContent = 'Split Completed';
        alert("已清除所有标记");
        setMode('foreground');
    };

    // 绘制框选的绿色虚线框（基于 CSS 坐标）
    function drawBoxOverlay() {
        // 先清空旧框
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

    // 更新左侧显示的坐标信息
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

    // 提交标注到后端
    window.submitPoints = function () {
        if (foregroundPoints.length + backgroundPoints.length === 0
            && boxPoints.length !== 2) {
            alert("请至少标注一个点或一个框。");
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
            alert("提交成功: " + data.message);
            renderResults(data.result);
            progressBar.value = 100;
            progress.style.display = "none";
            progressBar.value = 0;
            document.getElementById("selection-controls").style.display = "block";
            document.getElementById("segmentation-section").style.display = "block";
        })
        .catch(err => {
            console.error("submit failed", err);
            alert("提交失败");
        });
    };

    // 渲染后端返回的多结果（png + inverted）
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

            // 正向前景图
            const img1 = document.createElement("img");
            img1.src   = resultPaths[i] + "?t=" + Date.now();
            img1.alt   = `Mask ${i}`; 
            img1.style.width    = "400px";
            img1.style.objectFit= "contain";

            // 反转背景图
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
        alert("请先选择一个分割结果。");
        return;
    }
    const idx      = sel.value;
    const baseName = `result_${currentFilename.split('.')[0]}_${idx}`;
    const maskPath = `static/uploads/${baseName}_mask.png`;
    window.originalFileName  = currentFilename;
    window.selectedMaskPath  = maskPath;
    console.log("✔ originalFileName:", window.originalFileName);
    console.log("✔ selectedMaskPath:", window.selectedMaskPath);

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
        alert("Confirmed: " + d.message);
        document.getElementById("stylize-section").style.display = "block";  
    })
    .catch(err => console.error("Confirmation failed", err));
    }

    // 风格化处理函数：确认结果后点击触发
   // 只要选中 radio，就把按钮显示出来
window.onRegionSelect = function() {
  document.getElementById("apply-stylization-btn").style.display = "inline-block";
};

window.applyStylization = function() {
  const region = document.querySelector('input[name="stylizeRegion"]:checked');
  if (!region) {
    alert("请先选择风格化区域");
    return;
  }
  const styleType = region.value; // 'foreground' 或 'background'
  const maskPath = window.selectedMaskPath;
  const filename = window.originalFileName;
  fetch('/stylize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename, mask_path: maskPath, styleType })
  })
  .then(res => res.json())
  .then(data => {
    if (data.styled_path) {
        document.getElementById('styled-img').src = '/' + data.styled_path;
        // 隐藏分割结果区域
        document.getElementById('segmentation-section').style.display = 'none';
        // 显示风格化结果
        document.getElementById('styled-output').style.display = 'block';
    } else {
      alert("风格化失败");
    }
  })
  .catch(() => alert("风格化出错"));
};




}); 
