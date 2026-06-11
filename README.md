Efficient allocation of limited public-safety resources in urban environments requires full coverage of complex road networks at minimum cost. This repository provides an end-to-end pipeline that models urban road networks as graphs, identifies structural near-misses, and leverages Fixed-Parameter Tractable (FPT) algorithms to solve computationally hard domination problems for optimal resource deployment.
We model urban road networks as graphs where intersections are vertices and road segments are edges, seeking optimal dominating sets. While domination in arbitrary graphs is NP-hard, real-world road networks are almost structured. They closely resemble ideal graph classes, differing only by a small number of irregular vertices:
1) Interval Graphs
2) Block Graphs
3) Cluster Graphs
By exploiting this structural property via parameterized complexity, we isolate a small modulator set $S$ of size $k$. Its removal leaves the graph in the target structured class, allowing us to execute highly efficient FPT algorithms with a running time of the form: $f(k).poly(n)$

Installation and Setup:
1) Clone the repository:
git clone https://github.com/samrddhi-s/Parameterised-Road-Domination.git
cd Parameterised-Road-Domination

2) Install dependencies:
pip install -r requirements.txt

3) Run the pipeline:
python main.py --location "Your City/Region Name" --algorithm block
