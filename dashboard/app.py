# dashboard/app.py
# Dashboard Streamlit — Qualité de l'Eau distribuée en France
# Connexion à FastAPI via requests

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import requests
import pandas as pd
import os

# ============================================================
# Configuration de la page
# ============================================================
st.set_page_config(
    page_title="Qualité de l'Eau en France",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# URL de l'API FastAPI
# ============================================================
API_URL = os.environ.get("API_URL", "http://localhost:8000")

# ============================================================
# Fonction utilitaire — appel API avec cache
# ============================================================
@st.cache_data(ttl=300)
def appel_api(endpoint: str, params: dict = None):
    try:
        response = requests.get(f"{API_URL}/{endpoint}", params=params, timeout=30)
        response.raise_for_status()
        return pd.DataFrame(response.json()["data"])
    except Exception as e:
        st.error(f"Erreur API : {e}")
        return pd.DataFrame()

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/1200px-Python-logo-notext.svg.png", width=40)
    st.title("💧 Qualité de l'Eau")
    st.markdown("---")

    # Sélection du profil
    profil = st.radio(
        "Votre profil :",
        ["🏠 Citoyen", "🏛️ Institutionnel", "💻 Data / Technique"],
        index=0
    )

    st.markdown("---")

    # Navigation
    page = st.radio(
        "Navigation :",
        ["🏠 Accueil", "📍 Par commune", "📈 Évolution", "🗺️ Carte régions", "🏆 Top communes", "⚠️ Non-conformités"]
    )

    st.markdown("---")

    # Filtres globaux
    st.markdown("**Filtres**")
    annee = st.selectbox("Année", [2025, 2024, 2023], index=0)
    departement = st.text_input("Département (code)", placeholder="ex: 69")

    st.markdown("---")
    st.caption("Pipeline Qualité de l'Eau — Brief Simplon P1-2025")

# ============================================================
# PAGE ACCUEIL
# ============================================================
if page == "🏠 Accueil":
    st.title("💧 Qualité de l'Eau distribuée en France")

    if profil == "🏠 Citoyen":
        st.markdown("### Votre eau du robinet est-elle sûre ?")
        st.markdown("Ce tableau de bord analyse les résultats de **38 millions de contrôles sanitaires** réalisés commune par commune en France.")
    elif profil == "🏛️ Institutionnel":
        st.markdown("### Tableau de bord — Contrôle sanitaire de l'eau distribuée")
        st.markdown("Données issues du Système d'Information en Santé-Environnement sur les Eaux (SISE-Eaux), via data.gouv.fr.")
    else:
        st.markdown("### Pipeline Medallion — Bronze → Silver → Gold")
        st.markdown("38M lignes ingérées, transformées et validées via Apache Spark sur Databricks Free Edition.")

    st.markdown("---")

    # KPIs
    with st.spinner("Chargement des indicateurs..."):
        df_carte = appel_api("carte_regions")

    if not df_carte.empty:
        col1, col2, col3 = st.columns(3)

        conformite_nationale = df_carte["taux_conformite_pct"].mean() if "taux_conformite_pct" in df_carte.columns else 0
        nb_communes = df_carte["nb_communes"].sum() if "nb_communes" in df_carte.columns else 0
        nb_analyses = df_carte["nb_analyses"].sum() if "nb_analyses" in df_carte.columns else 0

        with col1:
            st.metric(
                label="Conformité nationale",
                value=f"{conformite_nationale:.1f}%",
                delta="Données SISE-Eaux"
            )
        with col2:
            st.metric(
                label="Communes analysées",
                value=f"{int(nb_communes):,}".replace(",", " ")
            )
        with col3:
            st.metric(
                label="Analyses réalisées",
                value=f"{int(nb_analyses):,}".replace(",", " ")
            )
    else:
        st.info("Connexion à l'API en cours...")

# ============================================================
# PAGE PAR COMMUNE
# ============================================================
elif page == "📍 Par commune":
    if profil == "🏠 Citoyen":
        st.title("📍 L'eau de ma commune est-elle sûre ?")
        commune_recherche = st.text_input("Recherchez votre commune", placeholder="ex: Lyon")
    elif profil == "🏛️ Institutionnel":
        st.title("📍 Conformité par commune")
        commune_recherche = st.text_input("Rechercher une commune", placeholder="ex: Lyon")
    else:
        st.title("📍 gold_conformite_commune — données complètes")
        commune_recherche = st.text_input("Filtrer par nom de commune", placeholder="ex: Lyon")

    with st.spinner("Chargement des données..."):
        params = {"limite": 500}
        if departement:
            params["departement"] = departement
        df_commune = appel_api("conformite_commune", params)

    if not df_commune.empty:
        # Filtre recherche commune
        if commune_recherche and "nom_commune" in df_commune.columns:
            df_commune = df_commune[
                df_commune["nom_commune"].str.contains(commune_recherche, case=False, na=False)
            ]

        if profil == "🏠 Citoyen":
            for _, row in df_commune.head(5).iterrows():
                taux = row.get("taux_conformite_pct", 0)
                statut = "✅ Eau conforme" if taux >= 95 else "⚠️ Vigilance recommandée"
                st.metric(
                    label=row.get("nom_commune", ""),
                    value=f"{taux:.1f}%",
                    delta=statut
                )
        elif profil == "🏛️ Institutionnel":
            colonnes = ["nom_commune", "code_departement", "nb_analyses", "taux_conformite_pct"]
            colonnes_dispo = [c for c in colonnes if c in df_commune.columns]
            st.dataframe(df_commune[colonnes_dispo], use_container_width=True)
        else:
            st.dataframe(df_commune, use_container_width=True)
            st.caption(f"Total : {len(df_commune)} communes")

        # Graphique barres
        if "nom_commune" in df_commune.columns and "taux_conformite_pct" in df_commune.columns:
            fig = px.bar(
                df_commune.head(20),
                x="nom_commune",
                y="taux_conformite_pct",
                color="taux_conformite_pct",
                color_continuous_scale=["red", "orange", "green"],
                title="Taux de conformité par commune (20 premières)",
                labels={"taux_conformite_pct": "Taux (%)", "nom_commune": "Commune"}
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

        st.download_button(
            label="Télécharger les données (CSV)",
            data=df_commune.to_csv(index=False),
            file_name="conformite_communes.csv",
            mime="text/csv"
        )

# ============================================================
# PAGE EVOLUTION
# ============================================================
# Architecture en deux temps :
# 1. Appel initial léger (limite=500) pour construire la liste des paramètres
#    disponibles dans le selectbox — on ne charge pas toute la table.
# 2. Une fois le paramètre sélectionné par l'utilisateur, appel ciblé
#    (parametre=<code>, limite=500) pour récupérer toutes les mesures
#    de ce paramètre sur la période 2023-2025.
# Ce pattern évite de charger 42 707 lignes en mémoire pour n'en afficher
# qu'une fraction, et garantit que chaque paramètre dispose de sa série
# temporelle complète pour le tracé Plotly.
# ============================================================
elif page == "📈 Évolution":
    if profil == "🏠 Citoyen":
        st.title("📈 L'eau s'améliore-t-elle dans le temps ?")
    elif profil == "🏛️ Institutionnel":
        st.title("📈 Évolution temporelle des paramètres")
    else:
        st.title("📈 gold_evolution_parametres — séries temporelles")

    # Etape 1 : chargement de la liste des paramètres disponibles (petit volume)
    with st.spinner("Chargement de la liste des paramètres..."):
        df_liste = appel_api("evolution_parametres", {"limite": 500})

    if not df_liste.empty and "code_parametre" in df_liste.columns:
        # Conversion en str et suppression des valeurs vides
        df_liste["code_parametre"] = df_liste["code_parametre"].fillna("").astype(str)
        parametres_dispo = sorted([
            p for p in df_liste["code_parametre"].unique().tolist() if p != ""
        ])

        if not parametres_dispo:
            st.warning("Aucun paramètre disponible.")
        else:
            # Sélection du ou des paramètres selon le profil
            if profil == "🏠 Citoyen":
                parametre_selectionne = st.selectbox(
                    "Choisir un paramètre",
                    parametres_dispo,
                    help="Un paramètre = un type de substance analysée dans l'eau"
                )
                parametres_filtres = [parametre_selectionne]
            elif profil == "🏛️ Institutionnel":
                parametre_selectionne = st.selectbox("Paramètre", parametres_dispo)
                parametres_filtres = [parametre_selectionne]
            else:
                parametres_filtres = st.multiselect(
                    "Paramètres (multi-sélection)",
                    parametres_dispo,
                    default=parametres_dispo[:3] if len(parametres_dispo) >= 3 else parametres_dispo
                )

            if parametres_filtres:
                # Etape 2 : chargement ciblé des données pour chaque paramètre sélectionné
                # L'API accepte un filtre parametre= pour ne retourner que les lignes utiles
                frames = []
                with st.spinner("Chargement des séries temporelles..."):
                    for p in parametres_filtres:
                        df_p = appel_api("evolution_parametres", {
                            "parametre": p,
                            "limite": 500
                        })
                        if not df_p.empty:
                            frames.append(df_p)

                if frames:
                    df_filtre = pd.concat(frames, ignore_index=True)
                    df_filtre["code_parametre"] = df_filtre["code_parametre"].fillna("").astype(str)

                    if "annee" in df_filtre.columns and "mois" in df_filtre.columns:
                        df_filtre = df_filtre.copy()
                        # Construction de la colonne periode en str propre YYYY-MM
                        df_filtre["periode"] = (
                            df_filtre["annee"].astype(str)
                            + "-"
                            + df_filtre["mois"].astype(str).str.zfill(2)
                        )
                        df_filtre = df_filtre.sort_values("periode")
                        periodes_ordre = sorted(df_filtre["periode"].unique().tolist())

                        fig = px.line(
                            df_filtre,
                            x="periode",
                            y="taux_conformite_pct",
                            color="code_parametre",
                            title="Evolution du taux de conformité par paramètre",
                            labels={
                                "taux_conformite_pct": "Taux (%)",
                                "periode": "Période",
                                "code_parametre": "Paramètre"
                            },
                            markers=True,
                            category_orders={"periode": periodes_ordre}
                        )
                        fig.update_xaxes(type="category")
                        fig.update_layout(xaxis_tickangle=-45)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("Colonnes 'annee' ou 'mois' absentes des données.")

                    if profil == "💻 Data / Technique":
                        st.dataframe(df_filtre, use_container_width=True)
                else:
                    st.info("Aucune donnée pour les paramètres sélectionnés.")
    else:
        st.info("Aucune donnée disponible.")

# ============================================================
# PAGE CARTE REGIONS
# ============================================================
elif page == "🗺️ Carte régions":
    if profil == "🏠 Citoyen":
        st.title("🗺️ La qualité de l'eau dans ma région")
        st.markdown("Chaque département est coloré selon son taux de conformité. Les **bassins hydrographiques** sont superposés pour montrer l'origine naturelle de votre eau.")
    elif profil == "🏛️ Institutionnel":
        st.title("🗺️ Carte nationale — conformité par département")
    else:
        st.title("🗺️ gold_carte_regions — choroplèthe + bassins hydrographiques")

    with st.spinner("Chargement des données cartographiques..."):
        df_carte = appel_api("carte_regions")

    if not df_carte.empty and "code_departement" in df_carte.columns:

        # Informations bassins hydrographiques — profil Citoyen uniquement
        if profil == "🏠 Citoyen":
            with st.expander("ℹ️ Comprendre les bassins hydrographiques"):
                st.markdown("""
                Un **bassin hydrographique** est le territoire drainé par un fleuve et ses affluents.
                En France, on distingue 6 grands bassins :
                - **Seine-Normandie** — Île-de-France, Normandie
                - **Loire-Bretagne** — Centre, Pays de la Loire, Bretagne
                - **Adour-Garonne** — Nouvelle-Aquitaine, Occitanie
                - **Rhône-Méditerranée** — Auvergne-Rhône-Alpes, PACA
                - **Rhin-Meuse** — Grand Est
                - **Artois-Picardie** — Hauts-de-France

                La **Directive Cadre Européenne sur l'Eau** (2000) organise la gestion de l'eau
                à l'échelle de ces bassins pour garantir la qualité de l'eau potable.
                """)

        # CORRECTION 4 : normalisation code_departement 3 chiffres → 2 chiffres
        # L'API retourne '001', '002' mais le GeoJSON gregoiredavid attend '01', '02'
        df_carte["code_departement"] = df_carte["code_departement"].astype(str).str.lstrip("0").str.zfill(2)

        # Filtrage sur l'année sélectionnée pour n'afficher qu'une valeur par département
        df_carte_annee = df_carte[df_carte["annee"] == annee] if "annee" in df_carte.columns else df_carte

        fig = px.choropleth(
            df_carte_annee,
            geojson="https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-version-simplifiee.geojson",
            locations="code_departement",
            featureidkey="properties.code",
            color="taux_conformite_pct",
            color_continuous_scale=["red", "orange", "green"],
            range_color=[80, 100],
            title=f"Taux de conformité par département ({annee})",
            labels={"taux_conformite_pct": "Conformité (%)"},
        )
        fig.update_geos(fitbounds="locations", visible=False)
        fig.update_layout(height=600, margin={"r": 0, "t": 30, "l": 0, "b": 0})
        st.plotly_chart(fig, use_container_width=True)

        # Heatmap supplémentaire pour profil Data / Technique
        if profil == "💻 Data / Technique" and "annee" in df_carte.columns:
            fig_heat = px.density_heatmap(
                df_carte,
                x="annee",
                y="code_departement",
                z="taux_conformite_pct",
                title="Heatmap conformité — départements × années",
                labels={"taux_conformite_pct": "Conformité (%)"}
            )
            st.plotly_chart(fig_heat, use_container_width=True)

        if profil != "🏠 Citoyen":
            st.dataframe(df_carte, use_container_width=True)

    else:
        st.warning("Données cartographiques indisponibles.")

# ============================================================
# PAGE TOP COMMUNES
# ============================================================
elif page == "🏆 Top communes":
    if profil == "🏠 Citoyen":
        st.title("🏆 Les communes avec la meilleure eau de France")
    elif profil == "🏛️ Institutionnel":
        st.title("🏆 Classement des communes — Top et Flop")
    else:
        st.title("🏆 gold_top_communes — RANK() par département")

    with st.spinner("Chargement du classement..."):
        params_top = {"limite": 10, "ordre": "desc"}
        params_flop = {"limite": 10, "ordre": "asc"}
        if departement:
            params_top["departement"] = departement
            params_flop["departement"] = departement
        df_top = appel_api("top_communes", params_top)
        df_flop = appel_api("top_communes", params_flop)

    if not df_top.empty:
        if profil == "🏠 Citoyen":
            st.markdown("### Podium national 🥇")
            for _, row in df_top.head(10).iterrows():
                rang = row.get("rang", "")
                nom = row.get("nom_commune", "")
                taux = row.get("taux_conformite_pct", 0)
                medaille = "🥇" if rang == 1 else "🥈" if rang == 2 else "🥉" if rang == 3 else f"#{rang}"
                st.markdown(f"**{medaille} {nom}** — {taux:.1f}% de conformité")

        # Graphique Top
        fig_top = px.bar(
            df_top,
            x="taux_conformite_pct",
            y="nom_commune",
            orientation="h",
            color="taux_conformite_pct",
            color_continuous_scale=["orange", "green"],
            title=f"Top {len(df_top)} communes — meilleur taux de conformité",
            labels={"taux_conformite_pct": "Taux (%)", "nom_commune": "Commune"}
        )
        fig_top.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_top, use_container_width=True)

        # Graphique Flop — communes avec le taux le plus bas
        if not df_flop.empty:
            fig_flop = px.bar(
                df_flop,
                x="taux_conformite_pct",
                y="nom_commune",
                orientation="h",
                color="taux_conformite_pct",
                color_continuous_scale=["red", "orange"],
                title=f"Flop {len(df_flop)} communes — taux de conformité les plus bas",
                labels={"taux_conformite_pct": "Taux (%)", "nom_commune": "Commune"}
            )
            fig_flop.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_flop, use_container_width=True)

        if profil == "💻 Data / Technique":
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Top 10**")
                st.dataframe(df_top, use_container_width=True)
            with col2:
                st.markdown("**Flop 10**")
                st.dataframe(df_flop, use_container_width=True)

# ============================================================
# PAGE NON-CONFORMITES
# ============================================================
elif page == "⚠️ Non-conformités":
    if profil == "🏠 Citoyen":
        st.title("⚠️ Quels contaminants ont été détectés ?")
        st.markdown("Ces résultats concernent les analyses **non conformes** aux normes sanitaires. Ils sont rares — moins de 2% des analyses au total.")
    elif profil == "🏛️ Institutionnel":
        st.title("⚠️ Paramètres non conformes — analyse détaillée")
    else:
        st.title("⚠️ gold_nonconformites — 12 cas documentés")
        st.info("Note : seulement 12 cas de non-conformité après correction de la logique qualitparam en Silver. Limitation documentée.")

    with st.spinner("Chargement des non-conformités..."):
        params = {}
        if annee:
            params["annee"] = annee
        df_nonconf = appel_api("nonconformites", params)

    if not df_nonconf.empty:
        if profil == "🏠 Citoyen":
            st.markdown("### Substances détectées")
            for _, row in df_nonconf.iterrows():
                # CORRECTION 5 : nom de colonne adapté à ce que retourne l'API
                nb_communes_val = row.get("nb_communes_concernees", row.get("nb_communes", "N/A"))
                st.warning(f"**{row.get('libelle_parametre', row.get('code_parametre', ''))}** — détecté dans {nb_communes_val} commune(s)")

        elif profil == "🏛️ Institutionnel":
            # CORRECTION 6 : colonnes alignées sur le schéma réel retourné par l'API
            colonnes = ["code_parametre", "libelle_parametre", "nb_analyses", "nb_non_conformes", "nb_communes_concernees", "annee"]
            colonnes_dispo = [c for c in colonnes if c in df_nonconf.columns]
            st.dataframe(df_nonconf[colonnes_dispo], use_container_width=True)

            if "code_parametre" in df_nonconf.columns and "nb_non_conformes" in df_nonconf.columns:
                df_plot = df_nonconf[df_nonconf["code_parametre"].notna()]
                fig = px.bar(
                    df_plot,
                    x="code_parametre",
                    y="nb_non_conformes",
                    title="Non-conformités par paramètre",
                    labels={"nb_non_conformes": "Nb non conformes", "code_parametre": "Paramètre"}
                )
                st.plotly_chart(fig, use_container_width=True)

        else:
            st.dataframe(df_nonconf, use_container_width=True)

            if "code_parametre" in df_nonconf.columns and "nb_analyses" in df_nonconf.columns:
                fig = px.treemap(
                    df_nonconf[df_nonconf["code_parametre"].notna()],
                    path=["code_parametre"],
                    values="nb_analyses",
                    title="Treemap non-conformités par paramètre"
                )
                st.plotly_chart(fig, use_container_width=True)
    else:
        if profil == "🏠 Citoyen":
            st.success("Aucune non-conformité détectée pour les filtres sélectionnés.")
        else:
            st.info("Aucune donnée disponible pour les filtres sélectionnés.")