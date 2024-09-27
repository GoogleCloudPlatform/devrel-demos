CREATE VECTOR INDEX my_index ON `rag_data.embeddings`(embeddings)
OPTIONS(distance_type='COSINE', index_type='IVF', ivf_options='{"num_lists": 1000}');