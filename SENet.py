import torchvision.transforms as transforms
#import torch.nn.functional as F
import torch.nn as nn
import torchvision
import torch
import torch.optim
import math
import torch.utils.model_zoo as model_zoo





transform = transforms.Compose([transforms.ToTensor(),
                                transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),
                                ])

train_data = torchvision.datasets.CIFAR10(root='./data',
                                          train=True,
                                          download=False,
                                          transform=torchvision.transforms.ToTensor())

train_loader = torch.utils.data.DataLoader(train_data,
                                           batch_size=100,
                                           shuffle=True,
                                           num_workers=2)

test_data = torchvision.datasets.CIFAR10(root='./data',
                                         train=False,
                                         download=False,
                                         transform=torchvision.transforms.ToTensor())

test_loader = torch.utils.data.DataLoader(test_data,
                                          batch_size=100,
                                          shuffle=True,
                                          num_workers=2)







def conv3x3(in_planes, out_planes, stride=1):
    """3x3 convolution with padding"""
    return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride,
                     padding=1, bias=False)

class BasicBlock(nn.Module):
    expansion = 1

    def __init__(self, inplanes, planes, stride=1, downsample=None):
        super(BasicBlock, self).__init__()
        self.conv1 = conv3x3(inplanes, planes, stride)
        self.bn1 = nn.BatchNorm2d(planes)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = conv3x3(planes, planes)
        self.bn2 = nn.BatchNorm2d(planes)
        self.downsample = downsample
        self.stride = stride

        if planes == 64:
            self.globalAvgPool = nn.AvgPool2d(56, stride=1)
        elif planes == 128:
            self.globalAvgPool = nn.AvgPool2d(28, stride=1)
        elif planes == 256:
            self.globalAvgPool = nn.AvgPool2d(14, stride=1)
        elif planes == 512:
            self.globalAvgPool = nn.AvgPool2d(7, stride=1)
        self.fc1 = nn.Linear(in_features=planes, out_features=round(planes / 16))
        self.fc2 = nn.Linear(in_features=round(planes / 16), out_features=planes)
        self.sigmoid = nn.Sigmoid()



    def forward(self, x):
        residual = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)

        if self.downsample is not None:
            residual = self.downsample(x)

        original_out = out
        out = self.globalAvgPool(out)
        out = out.view(out.size(0), -1)
        out = self.fc1(out)
        out = self.relu(out)
        out = self.fc2(out)
        out = self.sigmoid(out)
        out = out.view(out.size(0), out.size(1), 1, 1)
        out = out * original_out

        out += residual
        out = self.relu(out)

        return out



class SENet(nn.Module):

    def __init__(self, block, layers, num_classes=1000):
        self.inplanes = 64
        super(SENet, self).__init__()
        self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3,
                               bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        self.layer1 = self._make_layer(block, 64, layers[0])
        self.layer2 = self._make_layer(block, 128, layers[1], stride=2)
        self.layer3 = self._make_layer(block, 256, layers[2], stride=2)
        self.layer4 = self._make_layer(block, 512, layers[3], stride=2)
        self.avgpool = nn.AvgPool2d(7, stride=1)
        self.fc = nn.Linear(512 * block.expansion, num_classes)

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, math.sqrt(2. / n))
            elif isinstance(m, nn.BatchNorm2d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()

    def _make_layer(self, block, planes, blocks, stride=1):
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion:
            downsample = nn.Sequential(
                nn.Conv2d(self.inplanes, planes * block.expansion,
                          kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(planes * block.expansion),
            )

        layers = []
        layers.append(block(self.inplanes, planes, stride, downsample))
        self.inplanes = planes * block.expansion
        for i in range(1, blocks):
            layers.append(block(self.inplanes, planes))

        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)

        x = self.avgpool(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)

        return x




net = SENet(BasicBlock, [3, 4, 6, 3], **kwargs)

Loss_func = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(net.parameters(), lr=0.001)


for epoch in range(10):
    for i, data in enumerate(train_loader, 0):
        images, labels = data
        optimizer.zero_grad()
        outputs = net(images)
        loss = Loss_func(outputs, labels)
        loss.backward()
        optimizer.step()

        if i % 100 == 99:
            correct = 0
            test_times = 0
            for j, (test_images, test_labels) in enumerate(test_loader, 0):
                test_output = net(test_images)
                _, prediction = torch.max(test_output.data, 1)
                correct += (prediction == test_labels).sum()
                test_times += test_labels.size(0)
                accuracy = float(correct)/float(test_times)
            print('[%d,%5d]   Loss:%.3f' % (epoch + 1, i + 1, loss), '  Accuracy %.4f' % accuracy)




