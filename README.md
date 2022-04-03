# ds2022-mini-proj-1
Distributed Systems mini project 1 - Mutual exclusion in distributed systems
Implementation of [Ricart–Agrawala algorithm](https://en.wikipedia.org/wiki/Ricart%E2%80%93Agrawala_algorithm)

Full Description of the task is [here](https://courses.cs.ut.ee/LTAT.06.007/2022_spring/uploads/Main/Mini-project1-DS2022.pdf) 

---------

![Architecture](https://github.com/a3darekar/ds2022-mini-proj-1/blob/master/Architecture.jpg)

---------

```text
./
├── .gitignore ----------------------------------- list of files im git commits
├── README.md ------------------------------------ this documentation
├── LICENSE -------------------------------------- To be Added
├── constants.py --------------------------------- Default values and string literals
├── critical_section.py -------------------------- Implementation of Critical Section
├── process.py ----------------------------------- Thread based simulation of Process
├── process_service.py --------------------------- Decoupled-server service to spawn process thread tied to ConnectionService
├── connection_service.py ------------------------ Decoupled-client service to communicate with handler task and ProcessService
├── ra_program_server.py ------------------------- Entry point ListenerService to Spawn Threads and observe RA algorithm
├── ra_program_client.py ------------------------- Client input point to send method calls to ListenerService
└── requirements.txt ----------------------------- pip requirements file
```

---------

## Requirements:

- rpyc (Really! That's it ;)

## How to run?

1. Install the requirement (just the one) from requirements.txt
2. Open two command line interfaces. 
3. Run the server. Optionally, pass `--verbose` flag to see algorithm's message hand-off logs.
```sh
	python ra_program_server.py
```
4. Run the client. Here, `N` denotes number of processes to be initialized.
```sh
	python ra_program_client.py N
```

## Commands: 

1. List: List processes and their current state. 
```sh
    $ list
```
2. time-p: Update upper bound for timeout of processes. `t` represents timeout in seconds.
```sh
    $ time-p t
```
3. time-cs: Update upper bound for timeout of Critical Section. `t` represents timeout in seconds.
```sh
    $ time-cs
```
4. exit: Terminate all threads, connections and release all acquired ports and exit program. 
```sh
    $ exit
```

## TODO:

1. More Testing.
2. Observe effect of asynchronous callbacks over synchronous.
3. Documentation.