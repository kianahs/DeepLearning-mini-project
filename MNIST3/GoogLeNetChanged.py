import torch
import torchvision
import torchvision.transforms as transforms
from torch import nn, optim
from torchvision.models import googlenet
from torch.utils.data.sampler import SubsetRandomSampler
import numpy as np
import os
import datetime  

aug = 1

def prepare_data(batch_size, mean, std, resize, random_crop_size,valid_split):
    

    transform = transforms.Compose([
        transforms.Resize(resize),               
        transforms.RandomHorizontalFlip(),  
        transforms.RandomRotation(15),  
        transforms.RandomCrop(random_crop_size, padding=4),  
        transforms.ToTensor(),               
        transforms.Normalize((mean,), (std,))  
    ])



    trainset = torchvision.datasets.MNIST(root='./data', train=True,
                                        download=True, transform=transform)
    testset = torchvision.datasets.MNIST(root='./data', train=False,
                                        download=True, transform=transform)



    num_train = len(trainset)
    indices = list(range(num_train))
    split = int(np.floor(valid_split * num_train))

    np.random.shuffle(indices)
    train_idx, valid_idx = indices[split:], indices[:split]

    train_sampler = SubsetRandomSampler(train_idx)
    valid_sampler = SubsetRandomSampler(valid_idx)

    trainloader = torch.utils.data.DataLoader(trainset, batch_size=batch_size,
                                            sampler=train_sampler, num_workers=2)
    validloader = torch.utils.data.DataLoader(trainset, batch_size=batch_size,
                                            sampler=valid_sampler, num_workers=2)
    testloader = torch.utils.data.DataLoader(testset, batch_size=batch_size,
                                            shuffle=False, num_workers=2)
    
    return trainloader, validloader, testloader
        


def evaluate_model(loader, model):
    correct = 0
    total = 0
    total_loss = 0
    with torch.no_grad():
        for data in loader:
            images, labels = data[0].to(device), data[1].to(device)
            outputs = model(images)
            loss = criterion(outputs, labels)

            if isinstance(outputs, tuple):
                outputs = outputs[0] 
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            total_loss += loss.item()
    return 100 * correct / total, total_loss / len(loader)





learning_rate = 0.01
momentum = 0.9
num_epochs = 40
batch_size = 64
resize = 256
random_crop_size = 224


dir_name = "results/BS{}-E{}-lr{}-SGD-CE-MNIST".format(batch_size,num_epochs,learning_rate)
if aug == 1:
    dir_name = "results/BS{}-E{}-lr{}-AUG-SGD-CE-MNIST".format(batch_size,num_epochs,learning_rate)


current_path = os.getcwd()  
path = os.path.join(current_path, dir_name)  

if not os.path.exists(path):
    os.makedirs(path)


current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
with open(os.path.join(path,'log_train.txt'), 'a') as file:
        file.write(current_time + '\n')

information = "DATASET: MNIST\nMODEL GoogLeNet prebuilt-changed\nTOTAL EPOCHS : {}\nBATCH SIZE : {}\nLearning rate : {}\nLoss : Cross Entropy\nOptimizer: SGD".format(num_epochs,batch_size,  learning_rate)
if aug == 1:
    information = "DATASET: MNIST\nDATA AUGMENTATION + random crop {} random rotate\nMODEL GoogLeNet prebuilt-changed\nTOTAL EPOCHS : {}\nBATCH SIZE : {}\nLearning rate : {}\nLoss : Cross Entropy\nOptimizer: SGD".format(random_crop_size,num_epochs,batch_size,  learning_rate)

with open(os.path.join(path,'log_train.txt'), 'a') as file:
        file.write(information)
        
        
        
trainloader, validloader, testloader = prepare_data(batch_size = batch_size, 
                                                    mean = 0.1307,
                                                    std = 0.3081, 
                                                    resize = resize, 
                                                    random_crop_size= random_crop_size,
                                                    valid_split = 0.1)


model = googlenet(pretrained=False, aux_logits=True, init_weights=True)
model.conv1 = nn.Conv2d(1, 64, kernel_size=7, stride=2, padding=3)
model.fc = nn.Linear(1024, 10)  



criterion = nn.CrossEntropyLoss()
optimizer = optim.SGD(model.parameters(), lr=learning_rate, momentum=momentum)



device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
model.to(device)
print(device)



train_losses = []
train_accuracies = []
running_train_losses = []
running_train_accuracies = []
validation_losses = []
validation_accuracies = []


for epoch in range(num_epochs):  
    model.train()
    running_loss = 0.0
    total = 0
    correct = 0
    for i, data in enumerate(trainloader, 0):
        inputs, labels = data[0].to(device), data[1].to(device)

        optimizer.zero_grad()

        outputs = model(inputs)
        # loss = criterion(outputs, labels)

        if isinstance(outputs, tuple):
            output, aux1, aux2 = outputs
            loss1 = criterion(output, labels)
            loss2 = criterion(aux1, labels)
            loss3 = criterion(aux2, labels)
            loss = loss1 + 0.3 * (loss2 + loss3)  
        else:
            loss = criterion(outputs, labels)
        
        loss.backward()
        running_loss += loss.item()
        optimizer.step()

        if isinstance(outputs, tuple):
            outputs = outputs[0]  
        _, predicted = torch.max(outputs.data, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()


    running_train_losses.append(running_loss/len(trainloader))
    running_train_accuracies.append(100 * correct / total)
    
    model.eval()
    train_accuracy, train_loss = evaluate_model(trainloader, model)
    valid_accuracy, valid_loss = evaluate_model(validloader, model)
    train_losses.append(train_loss)
    train_accuracies.append(train_accuracy)
    validation_losses.append(valid_loss)
    validation_accuracies.append(valid_accuracy)
    
    log_info = f'\nEpoch {epoch+1}\nTrain mode:\nTrain Loss: {running_train_losses[-1]:.5f}, Train Acc: {running_train_accuracies[-1]:.5f}%\n'
    log_info += f'Evaluate mode:\nTrain Loss: {train_loss:.5f}, Train Acc: {train_accuracy:.5f}%\nVal Loss: {valid_loss:.5f}, Val Acc: {valid_accuracy:.5f}%\n\n'
    
    print(log_info)
    
    
    with open(os.path.join(path,'log_train.txt'), 'a') as file:
        file.write(log_info)
        
        
print('Finished Training')


test_accuracy, test_loss = evaluate_model(testloader, model)
log_info = f'Test Loss: {test_loss:.5f}, Test Acc: {test_accuracy:.5f}%'
print(log_info)

with open(os.path.join(path,'log_train.txt'), 'a') as file:
        file.write(log_info)


model_name = "model-GoogLeNet-prebuilt-changed-BS{}-E{}-lr{}-SGD-CE-MNIST.pt".format(batch_size,num_epochs,learning_rate)
if aug == 1:
    model_name = "model-GoogLeNet-prebuilt-changed-BS{}-E{}-lr{}-AUG-SGD-CE-MNIST.pt".format(batch_size,num_epochs,learning_rate)

torch.save(model, os.path.join(path,model_name))

with open(os.path.join(path,'losses-and-accuracies.txt'), 'a') as file:
    file.write('Running train Losses and accuracies \n')
    file.write(str(running_train_losses)+'\n')
    file.write(str(running_train_losses)+'\n')
    file.write('Losses train valid test\n')
    file.write(str(train_losses)+'\n')
    file.write(str(validation_losses)+'\n')
    file.write(str(test_loss)+'\n')
    file.write('Accuracies train valid test\n')
    file.write(str(train_accuracies)+'\n')
    file.write(str(validation_accuracies)+'\n')
    file.write(str(test_accuracy)+'\n')
        