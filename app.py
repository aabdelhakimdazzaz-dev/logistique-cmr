import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="LogiTrans Pro CMR", layout="wide", page_icon="🚛")

@st.cache_data(ttl=300)
def load_data():
    SHEET_ID = "1fPhkHjoxYeqCz-x8V9f37wdBjsuSKpMdoA45CVBdlYE"
    url_cmd = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Commandes_Jour"
    url_cam = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Camions"
    
    commandes = pd.read_csv(url_cmd)
    camions = pd.read_csv(url_cam)
    
    commandes.columns = commandes.columns.str.strip()
    camions.columns = camions.columns.str.strip()
    
    for col in ['Poids_KG', 'Volume_m3', 'Valeur_Marchandise_EUR']:
        if col in commandes.columns:
            commandes[col] = pd.to_numeric(commandes[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    
    for col in ['Capacite_KG', 'Capacite_Volume_m3', 'Conso_L/100km', 'CP_KM', 'Prix_Jour_MAD', 'Cout_Fixe_Jour']:
        if col in camions.columns:
            camions[col] = pd.to_numeric(camions[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    
    return commandes, camions

DISTANCES = {
    ('Tanger', 'Madrid'): 1200, ('Tanger', 'Barcelona'): 1400, ('Tanger', 'Paris'): 1900,
    ('Tanger', 'Lyon'): 1700, ('Casablanca', 'Madrid'): 1000, ('Tanger', 'Tetouan'): 60, 
    ('Tanger', 'Larache'): 90, ('Tanger', 'Asilah'): 45, ('Casablanca', 'Rabat'): 90,
}

def get_distance(ville1, ville2):
    return DISTANCES.get((ville1, ville2), DISTANCES.get((ville2, ville1), 800))

try:
    df_cmd, df_camions = load_data()
except Exception as e:
    st.error(f"Erreur chargement: {e}")
    st.info("⚠️ Vérifi: Partager → Tous avec le lien → Lecteur")
    st.stop()

st.title("🚛 LogiTrans Pro CMR")
st.caption(f"Données: {len(df_cmd)} commandes | {len(df_camions)} camions")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📦 Groupage TNG", "💰 Rentabilité", "📄 Facturation", "📊 KPI CP/CPK", "📈 Dashboard"])

with tab1:
    st.header("🚛 Optimisation Groupage Tanger")
    grp_tng = df_cmd[(df_cmd['Type_Chargement'] == 'Groupage') & (df_cmd['Lieu_Groupage'] == 'Tanger') & (df_cmd['Statut'] == 'En_attente')].copy()
    if len(grp_tng) == 0:
        st.warning("⚠️ Ma kaynch commandes groupage Tanger en attente")
    else:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Commandes", len(grp_tng))
        col2.metric("Volume", f"{grp_tng['Volume_m3'].sum():.0f} m³")
        col3.metric("Poids", f"{grp_tng['Poids_KG'].sum():.0f} kg")
        col4.metric("Valeur", f"{grp_tng['Valeur_Marchandise_EUR'].sum():.0f} EUR")
        st.dataframe(grp_tng[['ID_Commande', 'Client', 'Ville_Client', 'Poids_KG', 'Volume_m3']], hide_index=True, width='stretch')
        
        if st.button("🚀 Lancer l'Optimisation", type="primary", width='stretch'):
            CAPACITE_CAMION = 90
            total_vol = grp_tng['Volume_m3'].sum()
            nb_camions = int(np.ceil(total_vol / CAPACITE_CAMION))
            st.success(f"✅ Besoin de **{nb_camions} camions** | Remplissage: {total_vol/(nb_camions*90)*100:.0f}%")
            
            grp_tng_sorted = grp_tng.sort_values('Volume_m3', ascending=False)
            camions_plan = [[] for _ in range(nb_camions)]
            volumes_camions = [0] * nb_camions
            
            for _, cmd in grp_tng_sorted.iterrows():
                for i in range(nb_camions):
                    if volumes_camions[i] + cmd['Volume_m3'] <= CAPACITE_CAMION:
                        camions_plan[i].append(cmd)
                        volumes_camions[i] += cmd['Volume_m3']
                        break
            
            for i, cmds in enumerate(camions_plan):
                if cmds:
                    with st.expander(f"🚚 Camion {i+1} - {volumes_camions[i]:.1f}/90 m³", expanded=True):
                        st.dataframe(pd.DataFrame(cmds)[['ID_Commande', 'Client', 'Ville_Client', 'Volume_m3']], hide_index=True)

with tab2:
    st.header("💰 Calcul Rentabilité")
    commande_id = st.selectbox("Commande", df_cmd['ID_Commande'].tolist())
    camion_sel = st.selectbox("Camion", df_camions['Matricule'].tolist())
    cmd = df_cmd[df_cmd['ID_Commande'] == commande_id].iloc[0]
    camion = df_camions[df_camions['Matricule'] == camion_sel].iloc[0]
    
    ville_depart = cmd.get('Lieu_Groupage', camion['Ville_Base']) if cmd['Type_Chargement']=='Groupage' else camion['Ville_Base']
    distance = get_distance(ville_depart, cmd['Ville_Client'])
    cout_transport = camion['CP_KM'] * distance + camion['Cout_Fixe_Jour']
    ca = cmd['Valeur_Marchandise_EUR'] * 10.5
    marge = ca - cout_transport
    taux_marge = (marge / ca * 100) if ca > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Distance", f"{distance} km")
    col2.metric("Coût", f"{cout_transport:,.0f} MAD")
    col3.metric("Marge", f"{marge:,.0f} MAD", f"{taux_marge:.1f}%")

with tab3:
    st.header("📄 Facturation")
    commandes_facture = st.multiselect("Commandes", df_cmd['ID_Commande'].tolist())
    if commandes_facture:
        df_fact = df_cmd[df_cmd['ID_Commande'].isin(commandes_facture)]
        total_ht = df_fact['Valeur_Marchandise_EUR'].sum() * 10.5
        st.metric("Total TTC", f"{total_ht*1.2:,.2f} MAD")
        st.dataframe(df_fact, hide_index=True)

with tab4:
    st.header("📊 KPI CP/CPK - Suis-je Capable?")
    col1, col2 = st.columns(2)
    with col1:
        camion_select = st.selectbox("Camion", df_camions['Matricule'].tolist(), key="cp")
        cam = df_camions[df_camions['Matricule'] == camion_select].iloc[0]
        ville_dest = st.selectbox("Destination", ['Madrid', 'Paris', 'Barcelona', 'Lyon'])
        dist = get_distance(cam['Ville_Base'], ville_dest)
        cout_total = cam['CP_KM'] * dist + cam['Cout_Fixe_Jour']
        st.metric("CP", f"{cam['CP_KM']:.2f} DH/km")
        st.metric("Coût Total", f"{cout_total:,.0f} MAD")
    
    with col2:
        commande_cpk = st.selectbox("Commande", df_cmd['ID_Commande'].tolist(), key="cpk")
        cmd_cpk = df_cmd[df_cmd['ID_Commande'] == commande_cpk].iloc[0]
        if cmd_cpk['Poids_KG'] > 0:
            cpk = cout_total / cmd_cpk['Poids_KG']
            cpk_max = st.number_input("CPK Max Client (DH/kg)", value=0.50)
            if cpk <= cpk_max:
                st.success(f"✅ CAPABLE - CPK: {cpk:.3f} DH/kg")
                st.balloons()
            else:
                st.error(f"❌ PAS CAPABLE - CPK: {cpk:.3f} DH/kg")

with tab5:
    st.header("📈 Dashboard")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Commandes", len(df_cmd))
    col2.metric("En Attente", len(df_cmd[df_cmd['Statut']=='En_attente']))
    col3.metric("Volume", f"{df_cmd['Volume_m3'].sum():,.0f} m³")
    col4.metric("CA", f"{(df_cmd['Valeur_Marchandise_EUR']*10.5).sum():,.0f} MAD")
    st.bar_chart(df_cmd['Type_Operation'].value_counts())

st.divider()
st.caption("LogiTrans Pro CMR © 2026")
