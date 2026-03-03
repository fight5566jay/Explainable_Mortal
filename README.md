This project is to generate human-understandable information from Mortal (a Riichi Mahjong AI).

For using the AI only, please access to the original project:

https://github.com/Equim-chan/Mortal

## Usage
------- A. Train your mortal -------
1. Build podman
```console
$ podman build -f Dockerfile.explainable-mortal -t explainable-mortal .
```

2.0. You can run python code in the podman container by "simple_run.sh".
```console
$ cd mortal
$ ./scripts/simple_run.sh [--skip-build-libriichi] [your_python].py [your_args]...
```

2. Prepare training data (You need to collect or generate by yourself).
   Put the data in mortal/built/dataset/.

3. Setup initial mortal.pth and grp.pth in mortal/built/models.
```console
$ Generate a random-weighted mortal model
$ ./scripts/simple_run.sh [--skip-build-libriichi] generate_random_model.py
$
$ Then, rename random_mortal.pth to mortal.pth
$ mv built/models/random_mortal.pth built/models/mortal.pth
$
$ Generate a random grp model
$ ./scripts/simple_run.sh [--skip-build-libriichi] create_grp.py
```

4. Train mortal
```console
$ # --no-rename-tensorboard will rename the directory of current tensorboard, else the process will keep using the same directory.
$ ./scripts/run_train.sh [--skip-build-libriichi] [--no-rename-tensorboard]
```

------- B. Analyze your mortal and generate WWW-plots -------
```console
$ # --train_new_rg_models will rename the directory of current regression models, else the process will keep using the same directory.
$ ./scripts/simple_run.sh [--skip-build-libriichi] mortal_analyzer.py [--train_new_rg_models]
```
