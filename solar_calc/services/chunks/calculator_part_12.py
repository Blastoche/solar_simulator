        Args:
            consommation_annuelle: Consommation souhaitÃ©e (kWh)
        
        Returns:
            ConsumptionResult avec structure garantie
        """
        # Appeler fonction existante
        result_dict = self.calculate_consumption(consommation_annuelle)
        
        # Valider
        validate_consumption_result(result_dict)
        
        # DÃ©terminer source
        if consommation_annuelle is not None:
            source = 'formulaire'
        elif hasattr(self.installation, 'consommation_annuelle'):
            source = 'installation'
        else:
            source = 'defaut'
        
        # CrÃ©er objet structurÃ©
        return ConsumptionResult(
            annuelle=result_dict['annuelle'],
            monthly=result_dict['monthly'],
            daily=result_dict['daily'],
            source=source
        )
    
    def calculate_financial_normalized(
        self, 
        production: ProductionResult, 
        consumption: ConsumptionResult
    ) -> FinancialResult:
        """
        Calcule les donnÃ©es financiÃ¨res avec contrat garanti.
        
        CONTRAT :
            Input : ProductionResult + ConsumptionResult
            Output : FinancialResult avec payback calculÃ©
        
        Args:
            production: RÃ©sultat de production
            consumption: RÃ©sultat de consommation
        
        Returns:
            FinancialResult avec tous les indicateurs
        """
        # Convertir en dict pour fonction existante
        prod_dict = production.to_dict()
        cons_dict = consumption.to_dict()
        
        # Appeler fonction existante
        result_dict = self.calculate_financial(prod_dict, cons_dict)
        
        # CoÃ»t installation
        cout = self.puissance_kw * 1800  # â‚¬/kWc
        
        # CrÃ©er objet structurÃ© (calcule payback auto)
        return FinancialResult(
            economie_annuelle=result_dict['economie_annuelle'],
            roi_25ans=result_dict['roi'],
            taux_rentabilite=result_dict['taux_rentabilite'],
            cout_installation=cout
        )
