class TableParser:
    def parse(self, *args, **kwargs):
        tables = []
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                extracted = self.parse_table(page)
                if extracted:
                    tables.append({
                        "page": page_num,
                        "data": extracted
                    })
        return tables

    def parse_table(self, page_or_table):
        """
        Parse table from pdfplumber page or table data
        """
        if hasattr(page_or_table, 'extract_tables'):
            tables = page_or_table.extract_tables()
            if tables:
                for table in tables:
                    if table and any(any(cell for cell in row if cell) for row in table if row):
                        return table
            return []
        
        elif isinstance(page_or_table, list):
            return page_or_table
        
        return []

    def classify_table(self, table_data):
        """
        Classify table type based on content
        """
        if not table_data:
            return "unknown"
            
        # Flatten table content for analysis
        text_content = " ".join([
            " ".join(str(cell) for cell in row if cell) 
            for row in table_data if row
        ]).lower()
        
        # Classification logic
        if any(kw in text_content for kw in ["capital", "commitment", "call"]):
            return "capital_call"
        elif any(kw in text_content for kw in ["distribution", "payout"]):
            return "distribution"
        elif any(kw in text_content for kw in ["adjustment", "reconciliation"]):
            return "adjustment"
        else:
            return "unknown"