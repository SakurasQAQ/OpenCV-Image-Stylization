import torch
import torch.nn as nn

# === 定义 Residual Block ===
class ResnetBlock(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.conv_block = nn.Sequential(
            nn.ReflectionPad2d(1),
            nn.Conv2d(dim, dim, 3),
            nn.InstanceNorm2d(dim),
            nn.ReLU(True),
            nn.ReflectionPad2d(1),
            nn.Conv2d(dim, dim, 3),
            nn.InstanceNorm2d(dim)
        )

    def forward(self, x):
        return x + self.conv_block(x)

# === 定义 Generator ===
class Generator(nn.Module):
    def __init__(self, num_res_blocks=8):
        super().__init__()
        layers = [nn.ReflectionPad2d(3), nn.Conv2d(3, 64, 7), nn.InstanceNorm2d(64), nn.ReLU(True)]
        in_ch = 64
        for _ in range(2):
            layers += [nn.Conv2d(in_ch, in_ch * 2, 3, stride=2, padding=1),
                       nn.InstanceNorm2d(in_ch * 2), nn.ReLU(True)]
            in_ch *= 2
        for _ in range(num_res_blocks):
            layers += [ResnetBlock(in_ch)]
        for _ in range(2):
            layers += [nn.ConvTranspose2d(in_ch, in_ch // 2, 3, stride=2, padding=1, output_padding=1),
                       nn.InstanceNorm2d(in_ch // 2), nn.ReLU(True)]
            in_ch //= 2
        layers += [nn.ReflectionPad2d(3), nn.Conv2d(64, 3, 7), nn.Tanh()]
        self.model = nn.Sequential(*layers)

    def forward(self, x):
        return self.model(x)
