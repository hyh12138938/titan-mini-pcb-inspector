# -*- coding: utf-8 -*-
"""
Titan Board Mini —— 焊盘"有件 / 无件"二分类训练脚本

用途：
    1. 读取 D:\\RTT\\dataset\\pad\\{yes,no}\\*.jpg
    2. 用 MobileNetV2（可调宽度）微调，输入 96x96
    3. 输出 pad_model.pth（PyTorch）+ pad_model.onnx（给后面 TFLite 转换用）

用法（在 D:\\RTT\\ml 下）：
    ..\\ml\\venv\\Scripts\\python.exe train_pad.py
    ..\\ml\\venv\\Scripts\\python.exe train_pad.py --epochs 30 --unfreeze
    ..\\ml\\venv\\Scripts\\python.exe train_pad.py --data D:\\other\\dataset

注意：
    * 类别顺序由文件夹名排序决定：no=0, yes=1（ImageFolder 按字母序）。
      固件里也必须按同样顺序解释输出，否则 OK/NG 会反过来。
    * 图片少于 20 张时会自动跳过验证集（只训练，方便第一次跑通流程）。
"""
import argparse
import os
import sys
import time

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, models, transforms


def build_model(num_classes, cut=9, pretrained=True, img=96):
    """
    截断式迁移学习：
      * 用 ImageNet 预训练的 mobilenet_v2（全宽度 1.0，权重能对上）
      * 只保留前 cut 个 block（后面的砍掉）→ 参数从 4.2M 降到几十万
      * 接 AdaptiveAvgPool + 一个 Linear(num_classes)
    cut 越大越强也越大：
      cut=6  → 约 3 万参数，int8 约 40 KB
      cut=9  → 约 20 万参数，int8 约 200 KB
      cut=12 → 约 60 万参数，int8 约 600 KB
    """
    w = models.MobileNet_V2_Weights.IMAGENET1K_V1 if pretrained else None
    m = models.mobilenet_v2(weights=w)
    feats = m.features[:cut]
    with torch.no_grad():
        c = feats(torch.zeros(1, 3, img, img)).shape[1]
    head = nn.Sequential(
        nn.AdaptiveAvgPool2d(1),
        nn.Flatten(),
        nn.Dropout(0.2),
        nn.Linear(c, num_classes),
    )
    return nn.Sequential(feats, head)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default=r'D:\RTT\dataset\pad', help='数据集根目录（下面两个子目录 yes / no）')
    ap.add_argument('--out', default=r'D:\RTT\ml\out', help='模型输出目录')
    ap.add_argument('--img', type=int, default=96, help='输入分辨率（96/128）')
    ap.add_argument('--epochs', type=int, default=15)
    ap.add_argument('--batch', type=int, default=16)
    ap.add_argument('--lr', type=float, default=1e-3)
    ap.add_argument('--cut', type=int, default=9, help='保留前几个 block（6/9/12，越大越强越大）')
    ap.add_argument('--scratch', action='store_true', help='不用 ImageNet 预训练（默认用）')
    ap.add_argument('--workers', type=int, default=2)
    args = ap.parse_args()

    if not os.path.isdir(args.data):
        print(f'[错误] 数据目录不存在: {args.data}')
        sys.exit(1)

    os.makedirs(args.out, exist_ok=True)
    dev = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'[设备] {dev}  ' + (torch.cuda.get_device_name(0) if dev.type == 'cuda' else 'CPU'))

    # ---- 数据 ----
    tf_train = transforms.Compose([
        transforms.Resize((args.img, args.img)),
        transforms.RandomRotation(8),
        transforms.ColorJitter(brightness=0.25, contrast=0.25),
        transforms.ToTensor(),
        transforms.Normalize([0.5] * 3, [0.5] * 3),
    ])
    tf_eval = transforms.Compose([
        transforms.Resize((args.img, args.img)),
        transforms.ToTensor(),
        transforms.Normalize([0.5] * 3, [0.5] * 3),
    ])

    full = datasets.ImageFolder(args.data, transform=tf_train)
    classes = full.classes
    print(f'[类别] {classes}   (顺序 = 模型输出下标)')
    n = len(full)
    print(f'[样本] 共 {n} 张')
    for i, c in enumerate(classes):
        cnt = sum(1 for _, y in full.samples if y == i)
        print(f'         {i}:{c} = {cnt} 张')
    if n < 10:
        print('[错误] 样本太少（<10），先至少每类放 5 张')
        sys.exit(1)

    # 小于 20 张：不切验证集，直接全量训练
    if n >= 20:
        n_val = max(4, int(n * 0.2))
        n_train = n - n_val
        train_set, val_set = random_split(full, [n_train, n_val], generator=torch.Generator().manual_seed(42))
        val_set.dataset = datasets.ImageFolder(args.data, transform=tf_eval)
        # random_split 后 dataset 共享，这里重建 val 的 transform 不便，直接复用同一 transform（可接受）
        val_set.dataset.transform = tf_train
    else:
        train_set, val_set = full, None

    dl_train = DataLoader(train_set, batch_size=args.batch, shuffle=True, num_workers=args.workers)
    dl_val = DataLoader(val_set, batch_size=args.batch, shuffle=False, num_workers=args.workers) if val_set else None

    # ---- 模型 ----
    model = build_model(len(classes), args.cut, not args.scratch, args.img).to(dev)
    params = [p for p in model.parameters() if p.requires_grad]
    n_par = sum(p.numel() for p in model.parameters())
    print(f'[模型] 截断 MobileNetV2 cut={args.cut}  参数 {n_par/1e6:.3f} M  (int8 约 {n_par/1e6:.2f} MB)')
    opt = torch.optim.Adam(params, lr=args.lr)
    loss_fn = nn.CrossEntropyLoss()
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)

    best_acc, best_path = -1.0, os.path.join(args.out, 'pad_model.pth')
    t0 = time.time()

    for ep in range(1, args.epochs + 1):
        model.train()
        tot, correct, loss_sum = 0, 0, 0.0
        for x, y in dl_train:
            x, y = x.to(dev), y.to(dev)
            opt.zero_grad()
            out = model(x)
            loss = loss_fn(out, y)
            loss.backward()
            opt.step()
            loss_sum += loss.item() * x.size(0)
            correct += (out.argmax(1) == y).sum().item()
            tot += x.size(0)
        sched.step()
        tr_acc = 100.0 * correct / max(tot, 1)

        if dl_val is not None:
            model.eval()
            vt, vc = 0, 0
            with torch.no_grad():
                for x, y in dl_val:
                    x, y = x.to(dev), y.to(dev)
                    vc += (model(x).argmax(1) == y).sum().item()
                    vt += x.size(0)
            va = 100.0 * vc / max(vt, 1)
            print(f'epoch {ep:3d}/{args.epochs}  loss={loss_sum/max(tot,1):.4f}  train={tr_acc:5.1f}%  val={va:5.1f}%')
            if va > best_acc:
                best_acc = va
                torch.save(model.state_dict(), best_path)
        else:
            print(f'epoch {ep:3d}/{args.epochs}  loss={loss_sum/max(tot,1):.4f}  train={tr_acc:5.1f}%  (无验证集)')
            torch.save(model.state_dict(), best_path)

    print(f'[完成] 用时 {time.time()-t0:.1f}s   最佳验证准确率 {best_acc if best_acc>=0 else float("nan"):.1f}%')
    print(f'[保存] {best_path}')

    # ---- 导出 ONNX（后面转 TFLite 用）----
    model.load_state_dict(torch.load(best_path, map_location=dev))
    model.eval()
    dummy = torch.randn(1, 3, args.img, args.img, device=dev)
    onnx_path = os.path.join(args.out, 'pad_model.onnx')
    torch.onnx.export(
        model.cpu(), dummy.cpu(), onnx_path,
        input_names=['input'], output_names=['logits'],
        opset_version=13,
    )
    print(f'[保存] {onnx_path}')
    print('[下一步] 转 int8 TFLite -> Vela 编译 -> 塞进工程')


if __name__ == '__main__':
    main()
