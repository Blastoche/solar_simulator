    production_annuelle_kwh = models.FloatField(
        verbose_name="Production annuelle (kWh)"
    )
    production_specifique_kwh_kwc = models.FloatField(
        verbose_name="Production spÃ©cifique (kWh/kWc/an)"
    )
    
    # RÃ©sultats de consommation
    consommation_annuelle_kwh = models.FloatField(
        verbose_name="Consommation annuelle (kWh)"
    )
    
    # RÃ©sultats d'autoconsommation
    autoconsommation_kwh = models.FloatField(
        verbose_name="Autoconsommation (kWh)"
    )
    injection_reseau_kwh = models.FloatField(
        verbose_name="Injection rÃ©seau (kWh)"
    )
    achat_reseau_kwh = models.FloatField(
        verbose_name="Achat rÃ©seau (kWh)"
    )
    taux_autoconsommation_pct = models.FloatField(
        verbose_name="Taux d'autoconsommation (%)"
    )
    taux_autoproduction_pct = models.FloatField(
        verbose_name="Taux d'autoproduction (%)"
    )
    
    # DonnÃ©es horaires (stockage JSON compressÃ© ou fichier)
    donnees_horaires_url = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="URL des donnÃ©es horaires"
    )
    
    # Statut
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'En attente'),
            ('running', 'En cours'),
            ('completed', 'TerminÃ©e'),
            ('failed', 'Ã‰chouÃ©e'),
        ],
        default='pending',
        verbose_name="Statut"
    )
    
    # MÃ©tadonnÃ©es
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Simulation"
        verbose_name_plural = "Simulations"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Simulation {self.id} - {self.installation.nom} ({self.status})"
    
    @property
    def economie_annuelle_estimee(self):
        """
        Ã‰conomie annuelle estimÃ©e (simplifiÃ©e).
        Tarif moyen : 0.2276 â‚¬/kWh
        """
        tarif_moyen = 0.2276
        economie = (
            self.autoconsommation_kwh * tarif_moyen +
            self.injection_reseau_kwh * 0.13  # Tarif vente surplus
        )
        return round(economie, 2)
