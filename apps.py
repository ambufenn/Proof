import streamlit as st
from google import genai
from google.genai import types

# --- 1. Setup Klien Gemini ---

# Mengambil kunci API dari Streamlit Secrets (atau environment variable lokal)
try:
    API_KEY = st.secrets["gemini_api_key"]
except KeyError:
    st.error("Kunci API Gemini tidak ditemukan. Pastikan Anda menyimpannya di st.secrets['gemini_api_key'] atau environment variable.")
    st.stop()

client = genai.Client(api_key=API_KEY)
model = 'gemini-2.5-flash' # Model cepat dan efisien

# --- 2. Fungsi Logika Utama (Proofreading) ---

def generate_optimized_content(prompt_type, input_text, rules_context):
    """
    Mengirim prompt ke model Gemini berdasarkan tipe permintaan.
    """
    if prompt_type == "Proofreading & Peningkatan Bahasa":
        system_instruction = f"""
        Anda adalah Editor Akademik tingkat Scopus Q1.
        Tugas Anda adalah melakukan proofreading mendalam (tata bahasa, ejaan, konsistensi istilah)
        dan meningkatkan kejelasan, kepadatan, dan formalitas bahasa akademik
        sesuai standar publikasi jurnal.

        ### Aturan Gaya Penulisan Tambahan:
        {rules_context}
        
        Tampilkan hasil Anda dalam dua bagian yang jelas: "ORIGINAL TEXT" dan "REVISED TEXT".
        """
        user_prompt = f"Lakukan proofreading pada teks ini:\n\n{input_text}"

    elif prompt_type == "Templating & Copywriting Abstrak":
        system_instruction = f"""
        Anda adalah Asisten Penulisan Jurnal Scopus Q1.
        Tugas Anda adalah menyusun ulang konten draft (judul dan abstrak) agar sesuai
        dengan TEMPLATE JURNAL Q1 (gunakan aturan di bawah). Buat abstrak
        yang sangat persuasif dan menarik (copywriting).

        ### Aturan Templating Jurnal Q1:
        {rules_context} 
        
        Hasilkan output dalam template berikut:
        
        **JUDUL (Dioptimalkan untuk SEO dan Keterbacaan):**
        **PENULIS/AFILIASI:**
        **ABSTRAK (Maksimal 250 kata, persuasif):**
        **Kata Kunci:**
        """
        user_prompt = f"Susun ulang data mentah ini (gunakan baris pertama sebagai Judul, dan sisanya sebagai draft Abstrak):\n\n{input_text}"

    else:
        return "Tipe permintaan tidak valid."

    
    # Konfigurasi dan Pemanggilan API
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=0.3 # Suhu rendah untuk hasil yang lebih faktual/akurat
    )

    with st.spinner("Memproses dengan model Gemini..."):
        try:
            response = client.models.generate_content(
                model=model,
                contents=user_prompt,
                config=config
            )
            return response.text
        except Exception as e:
            st.error(f"Terjadi kesalahan saat memanggil API: {e}")
            return None


# --- 3. Antarmuka Streamlit ---

st.title("✍️ Gemini Scopus Q1 Editor")
st.markdown("Alat untuk *proofreading* dan *copywriting* akademik berbasis AI, dioptimalkan untuk standar publikasi jurnal berkualitas tinggi.")

# Pilihan Tipe Analisis
task_options = [
    "Pilih Tipe Analisis",
    "Proofreading & Peningkatan Bahasa",
    "Templating & Copywriting Abstrak"
]
selected_task = st.selectbox("Pilih Tugas yang Anda Inginkan:", task_options)

if selected_task != "Pilih Tipe Analisis":
    
    st.subheader("1. Masukkan Aturan Tambahan (Context Jurnal)")
    rules_context = st.text_area(
        "Contoh: Gunakan gaya sitasi APA 7th. Ubah semua 'penulis' menjadi 'peneliti'. Abstrak maksimal 250 kata.",
        height=100
    )
    
    st.subheader(f"2. Masukkan Teks untuk {selected_task}")
    if selected_task == "Templating & Copywriting Abstrak":
        input_label = "Masukkan Judul (baris 1) dan Draft Abstrak/Penulis (baris berikutnya)"
    else:
        input_label = "Masukkan Teks (misalnya, bagian Pendahuluan atau Metode)"
        
    input_text = st.text_area(input_label, height=300)

    if st.button("Jalankan Analisis", type="primary"):
        if not input_text:
            st.warning("Mohon masukkan teks untuk dianalisis.")
        else:
            result = generate_optimized_content(selected_task, input_text, rules_context)
            if result:
                st.subheader("🎉 Hasil Olahan Gemini")
                st.markdown(result)
