document.addEventListener("DOMContentLoaded", function () {

    let currentMode = 'foreground';
    const maxForeground = 5;
    const maxBackground = 2;

    let foregroundPoints = [];
    let backgroundPoints = [];

    let foregroundCount = 0;
    let backgroundCount = 0;

    let currentFilename = "";

    const img = document.getElementById("uploaded-image");
    const coords = document.getElementById("coords");
    const markerContainer = document.getElementById("marker-container");

    if (img && img.src) {
        const parts = img.src.split('/');
        currentFilename = parts[parts.length - 1];
    }

    img.addEventListener("click", function(event) {
        const rect = img.getBoundingClientRect();
        const x = Math.round(event.clientX - rect.left);
        const y = Math.round(event.clientY - rect.top);
        coords.textContent = `Clicked at (x: ${x}, y: ${y})`;

        if (currentMode === 'foreground' && foregroundPoints.length >= maxForeground) {
            alert("前景点不能超过 5 个！");
            return;
        }
        if (currentMode === 'background' && backgroundPoints.length >= maxBackground) {
            alert("背景点不能超过 2 个！");
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
    });

    window.setMode = function(mode) {
        currentMode = mode;
    };

    window.clearMarkers = function() {
        markerContainer.innerHTML = '';
        foregroundPoints = [];
        backgroundPoints = [];
        coords.textContent = '点击图片获取坐标';
        alert("Clean all dots");
    };

    window.submitPoints = function() {
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
        .then(res => res.json())
        .then(data => {
            alert("提交成功！后端返回：" + data.message);
            const resultImg = document.getElementById("resultImage");
            resultImg.src = data.result + '?t=' + new Date().getTime(); 
            console.log(data.result)
        })
        .catch(err => {
            console.error("提交失败", err);
        });
    };

});
