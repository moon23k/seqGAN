import os
import time
import math
import json
import tqdm
from collections import defaultdict

import torch
import torch.nn as nn
import torch.optim as optim

from utils.data import get_dataloader
from model.module import Generator
from utils.train import gen_train_epoch, gen_eval_epoch, epoch_time, set_seed, init_xavier, Config





def run(config):
    #set checkpoint, record path
    chk_dir = "checkpoints/"
    os.makedirs(chk_dir, exist_ok=True)
    chk_path = os.path.join(chk_dir, 'gen_states.pt')

    record = defaultdict(list)
    record_path = os.path.join(chk_dir, 'gen_record.json')


    #Set Generator Training Tools
    generator = Generator(config).to(config.device)
    generator.apply(init_xavier)
    criterion = nn.CrossEntropyLoss(ignore_index=config.pad_idx).to(config.device)
    optimizer = optim.Adam(generator.parameters(), lr=config.learning_rate)



    #Pretrain Generator
    train_dataloader = get_dataloader('gen', 'train', config.batch_size)
    valid_dataloader = get_dataloader('gen', 'valid', config.batch_size)
    print('--- Pretraining Generator ---')
    record_time = time.time()

    for epoch in range(config.gen_epochs):
        start_time = time.time()

        train_loss = gen_train_epoch(generator, train_dataloader, criterion, optimizer, config.device)
        valid_loss = gen_eval_epoch(generator, train_dataloader, criterion, config.device)
        
        end_time = time.time()
        epoch_mins, epoch_secs = epoch_time(start_time, end_time)


        #save training records
        record['epoch'].append(epoch+1)
        record['train_loss'].append(train_loss)
        record['valid_loss'].append(valid_loss)
        record['lr'].append(optimizer.param_groups[0]['lr'])


        #save best model
        if valid_loss < config.best_valid_loss:
            config.best_valid_loss = valid_loss
            torch.save({'epoch': epoch + 1,
                        'model': generator.state_dict(),
                        'optimizer': optimizer.state_dict(),
                        'train_loss': train_loss,
                        'valid_loss': valid_loss}, chk_path)

        print(f" Epoch {epoch + 1} / {config.gen_epochs} | Spent Time: {epoch_mins}m {epoch_secs}s")
        print(f'   Train Loss: {train_loss:.3f} | Valid Loss: {valid_loss:.3f}')


    train_mins, train_secs = epoch_time(record_time, time.time())
    record['train_time'].append(f"{train_mins}min {train_secs}sec")


    #save ppl score to train_record
    for (train_loss, valid_loss) in zip(record['train_loss'], record['valid_loss']):
        train_ppl = math.exp(train_loss)
        valid_ppl = math.exp(valid_loss)

        record['train_ppl'].append(round(train_ppl, 2))
        record['valid_ppl'].append(round(valid_ppl, 2))


    #save train_record to json file
    with open(record_path, 'w') as fp:
        json.dump(record, fp)




if __name__ == '__main__':    
    set_seed()
    config = Config()
    run(config)