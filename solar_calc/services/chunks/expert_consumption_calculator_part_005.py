        
        projections = []
        
        for annee in range(1, 11):
            conso = total_annuel * ((1 + evolution_conso) ** annee)
            prix_kwh = (cout_actuel / total_annuel) * ((1 + inflation_energie) ** annee)
            cout = conso * prix_kwh
            
            projections.append({
                'annee': 2026 + annee,
                'consommation_kwh': round(conso, 0),
                'prix_moyen_kwh': round(prix_kwh, 4),
                'cout_total': round(cout, 2),
            })
        
        return projections
