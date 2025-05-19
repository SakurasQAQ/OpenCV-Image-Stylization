import os
import glob
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms, utils
from torchvision.models import vgg19
from PIL import Image

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# -------------------------
# Dataset
# -------------------------
class ImageFolderDataset(Dataset):
    def __init__(self, root_dir, transform=None):
        self.paths = glob.glob(os.path.join(root_dir, "*.jpg")) + \
                     glob.glob(os.path.join(root_dir, "*.png"))
        self.transform = transform

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, idx):
        img = Image.open(self.paths[idx]).convert('RGB')
        if self.transform:
            img = self.transform(img)
        return img

# -------------------------
# Models
# -------------------------
class ResnetBlock(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.block = nn.Sequential(
            nn.ReflectionPad2d(1),
            nn.Conv2d(dim, dim, 3),
            nn.InstanceNorm2d(dim),
            nn.ReLU(True),
            nn.ReflectionPad2d(1),
            nn.Conv2d(dim, dim, 3),
            nn.InstanceNorm2d(dim)
        )
    def forward(self, x):
        return x + self.block(x)

class Generator(nn.Module):
    def __init__(self, res_blocks=8):
        super().__init__()
        layers = [nn.ReflectionPad2d(3), nn.Conv2d(3, 64, 7), nn.InstanceNorm2d(64), nn.ReLU(True)]
        c = 64
        for _ in range(2):
            layers += [nn.Conv2d(c, c*2, 3, stride=2, padding=1), nn.InstanceNorm2d(c*2), nn.ReLU(True)]
            c *= 2
        for _ in range(res_blocks): layers.append(ResnetBlock(c))
        for _ in range(2):
            layers += [nn.ConvTranspose2d(c, c//2, 3, stride=2, padding=1, output_padding=1),
                       nn.InstanceNorm2d(c//2), nn.ReLU(True)]
            c //= 2
        layers += [nn.ReflectionPad2d(3), nn.Conv2d(64, 3, 7), nn.Tanh()]
        self.net = nn.Sequential(*layers)
    def forward(self, x):
        return self.net(x)

class Discriminator(nn.Module):
    def __init__(self, in_c=3):
        super().__init__()
        layers = [nn.Conv2d(in_c, 64, 4, stride=2, padding=1), nn.LeakyReLU(0.2, True)]
        c = 64
        for nxt in [128, 256, 512]:
            layers += [nn.Conv2d(c, nxt, 4, stride=2, padding=1), nn.InstanceNorm2d(nxt), nn.LeakyReLU(0.2, True)]
            c = nxt
        layers.append(nn.Conv2d(c, 1, 4, padding=1))
        self.net = nn.Sequential(*layers)
    def forward(self, x):
        return self.net(x)

# -------------------------
# Losses
# -------------------------
mse = nn.MSELoss()
l1  = nn.L1Loss()

class PerceptualLoss(nn.Module):
    def __init__(self):
        super().__init__()
        vgg = vgg19(pretrained=True).features[:16].to(device)
        for p in vgg.parameters(): p.requires_grad=False
        self.vgg = vgg
    def forward(self, x, y):
        return l1(self.vgg((x+1)/2), self.vgg((y+1)/2))

def color_constancy(fake, style):
    mean_f = fake.mean([2,3])
    mean_s = style.mean([2,3])
    return l1(mean_f, mean_s)

def total_variation(x):
    tv_h = torch.mean(torch.abs(x[:,:,1:,:] - x[:,:,:-1,:]))
    tv_w = torch.mean(torch.abs(x[:,:,:,1:] - x[:,:,:,:-1]))
    return tv_h + tv_w

# -------------------------
# Training Loop (save only best model)
# -------------------------
def train():
    # Hyperparameters
    epochs = 50
    batch_size = 4
    lr = 2e-4
    lambda_perc = 10.0
    lambda_color = 5.0
    lambda_tv = 1e-6

    # Data loaders
    tf = transforms.Compose([
        transforms.Resize((256,256)),
        transforms.ToTensor(),
        transforms.Normalize([0.5]*3,[0.5]*3)
    ])
    photo_ds = ImageFolderDataset('dataset/photo', tf)
    style_ds = ImageFolderDataset('dataset/anime_style', tf)
    photo_loader = DataLoader(photo_ds, batch_size=batch_size, shuffle=True)
    style_loader = DataLoader(style_ds, batch_size=batch_size, shuffle=True)

    # Models
    G = Generator().to(device)
    D = Discriminator().to(device)
    G.apply(lambda m: nn.init.normal_(m.weight.data,0.0,0.02) if hasattr(m,'weight') else None)
    D.apply(lambda m: nn.init.normal_(m.weight.data,0.0,0.02) if hasattr(m,'weight') else None)

    # Losses and optimizers
    perc_loss = PerceptualLoss()
    opt_G = optim.Adam(G.parameters(), lr=lr, betas=(0.5,0.999))
    opt_D = optim.Adam(D.parameters(), lr=lr, betas=(0.5,0.999))
    sched_G = optim.lr_scheduler.StepLR(opt_G, step_size=30, gamma=0.5)
    sched_D = optim.lr_scheduler.StepLR(opt_D, step_size=30, gamma=0.5)

    best_loss = float('inf')

    for epoch in range(epochs):
        epoch_loss = 0.0
        iters = 0
        for photo, style in zip(photo_loader, style_loader):
            photo, style = photo.to(device), style.to(device)

            # Discriminator step
            with torch.no_grad(): fake = G(photo)
            real_label = torch.ones_like(D(style))
            fake_label = torch.zeros_like(D(fake))
            loss_D = mse(D(style), real_label) + mse(D(fake.detach()), fake_label)
            opt_D.zero_grad(); loss_D.backward(); opt_D.step()

            # Generator step
            fake = G(photo)
            adv = mse(D(fake), real_label)
            perc = perc_loss(fake, style)
            color = color_constancy(fake, style)
            tv = total_variation(fake)
            loss_G = adv + lambda_perc * perc + lambda_color * color + lambda_tv * tv
            opt_G.zero_grad(); loss_G.backward(); opt_G.step()

            epoch_loss += loss_G.item()
            iters += 1

        avg_loss = epoch_loss / iters if iters else float('inf')
        sched_G.step(); sched_D.step()

        # Save best model only
        if avg_loss < best_loss:
            best_loss = avg_loss
            os.makedirs('checkpoints', exist_ok=True)
            torch.save(G.state_dict(), 'checkpoints/AnimeGANv2_best.pth')
            print(f"Epoch {epoch}: new best avg_loss {avg_loss:.4f}, model saved.")
        else:
            print(f"Epoch {epoch}: avg_loss {avg_loss:.4f} (best {best_loss:.4f})")

if __name__ == '__main__':
    train()
