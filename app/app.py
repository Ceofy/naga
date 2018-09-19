import nbgwas
from nbgwas import Nbgwas

from flask import Flask, request
from flask_restful import reqparse, abort, Api, Resource

import pandas as pd
import networkx as nx

from call_biggim import get_table_from_biggim

app = Flask(__name__)
api = Api(app)

def create_gene_level_summary(genes, seeds): 
    # Add heat to gene_level_summary

    genes_level_summary = pd.DataFrame([genes], index=['Genes']).T
    genes_level_summary['p-value'] = 1
    genes_level_summary.loc[genes_level_summary['Genes'].isin(seeds), 'p-value'] = 0
    
    return genes_level_summary

class nbgwasapp(Resource): 

    def post(self): 

        print("Begin!")

        alpha = float(request.values.get("alpha", 0.5))

        print(request.files)
        
        if "network" in request.files: 
            print("Reading file")
            
            network_file = request.files['network']
            network_df = pd.read_csv(
                network_file.stream, 
                sep='\t', 
                names=['Gene1', 'Gene2', 'Val']
            )
        elif "column" in request.values: 
            print("Getting file from BigGIM")
            network_df = get_table_from_biggim(request.values['column'], 0.8)
            network_df = network_df.astype(str)
        
        else: 
            return "failed"
        
        print("Finished getting network_df")
        
        dG = nx.from_pandas_dataframe(network_df, 'Gene1', 'Gene2')

        print("Finished making network")

        seeds = request.values['seeds']
        seeds = seeds.split(',')

        print("Finished converting seeds")
        
        for i in seeds: 
            if i not in dG.nodes(): 
                seeds.remove(i) 
                print(f"{i} not in nodes")
                
                #return "failed"
            
        if len(seeds) == 0:
            print("No seeds left!")
            return "failed"

        gene_level_summary = create_gene_level_summary(dG.nodes(), seeds)

        print(gene_level_summary.head())

        print("Finished gene level Summary")

        g = Nbgwas(
            gene_level_summary=gene_level_summary,
            gene_col = 'Genes',
            gene_pval_col = 'p-value', 
            network=dG,
        )

        g.convert_to_heat()

        print(g.heat.head())

        g.diffuse(method='random_walk', alpha=alpha)

        print("Done!")

        print(g.heat.head())

        return g.heat.iloc[:, -1].to_json() + '\n'

        

# api.add_resource(HelloWorld, '/')
api.add_resource(nbgwasapp, '/nbgwas', endpoint='nbgwas')
#api.add_resource(job, '/nbgwas/<jobid>')

if __name__ == '__main__':
    app.run(debug=True) #Change this in production