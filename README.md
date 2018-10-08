# pic2move(編集中)
[pix2pix](https://phillipi.github.io/pix2pix/)をベースに入力画像から短い動画を生成する。


## セットアップ

### クローンして学習の実行

```sh
# clone
git clone https://github.com/a-kudoh/pic2move
cd pic2move

# train the model 
python pix2pix.py \
  --mode train \
  --output_dir train_output \
  --max_epochs 200 \
  --input_dir train_pic \
  --which_direction AtoB
```

