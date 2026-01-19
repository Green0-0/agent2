class ToolSettings:
    def __init__(self, max_search_result_listings=10, max_search_result_lines=40, 
                 max_view_lines_start=75, max_view_lines_end=75,
                 number_lines=False, unindent_inputs=True, reindent_outputs=True,
                 match_strict_level=1, secretly_save=True, 
                 embeddings_model_path=None, minimum_embeddings_similarity=0.5):
        self.max_search_result_listings = max_search_result_listings
        self.max_search_result_lines = max_search_result_lines
        self.max_view_lines_start = max_view_lines_start
        self.max_view_lines_end = max_view_lines_end
        self.number_lines = number_lines
        self.unindent_inputs = unindent_inputs
        self.reindent_outputs = reindent_outputs
        self.match_strict_level = match_strict_level
        self.secretly_save = secretly_save
        self.embeddings_model_path = embeddings_model_path
        self.embeddings_model = None
        self.minimum_embeddings_similarity = minimum_embeddings_similarity
        self.search_use_docstring = True
