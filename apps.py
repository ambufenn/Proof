import streamlit as st
from google import genai
from google.genai import types

# --- 0. Setup Klien Gemini & Konfigurasi ---

# Mengambil kunci API dari Streamlit Secrets
try:
    API_KEY = st.secrets["gemini_api_key"]
except KeyError:
    st.error("Kunci API Gemini tidak ditemukan. Pastikan Anda menyimpannya sebagai 'gemini_api_key'.")
    st.stop()

client = genai.Client(api_key=API_KEY)
MODEL = 'gemini-2.5-flash'
TEMPERATURE = 0.3 # Suhu rendah untuk konsistensi akademik

# --- 1. Fungsi Inti: Panggilan Model Gemini ---

def call_gemini_api(system_instruction, user_prompt):
    """
    Fungsi utilitas untuk memanggil Gemini API dengan konfigurasi yang konsisten.
    """
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=TEMPERATURE
    )

    with st.spinner("Memproses dengan Gemini Editor..."):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=user_prompt,
                config=config
            )
            return response.text
        except Exception as e:
            st.error(f"Terjadi kesalahan saat memanggil API: {e}")
            return None

# --- 2. Template Halaman Universal (Dengan Fitur Copy-Paste) ---

def render_content_page(title, instructions, action_type, rules_context_placeholder, specific_prompt_template):
    """
    Template Halaman untuk Copy Editing, Proofreading, dan Templating.
    Ditambahkan fitur Copy-Paste per segmentasi hasil.
    """
    st.header(title)
    st.markdown(instructions)

    st.subheader("1. Aturan Konteks Tambahan (Wajib)")
    context = st.text_area(
        "Masukkan aturan jurnal (e.g., gaya sitasi, batasan kata, formalitas):",
        value=rules_context_placeholder,
        height=100,
        key=f"{title}_context"
    )

    st.subheader("2. Teks Draft")
    input_text = st.text_area("Masukkan teks yang akan diproses:", height=300, key=f"{title}_input")

    # Inisialisasi state untuk menyimpan hasil
    if f"{title}_result" not in st.session_state:
        st.session_state[f"{title}_result"] = ""

    if st.button(f"Jalankan {action_type}", type="primary"):
        if not input_text or not context:
            st.warning("Mohon masukkan teks draft dan Aturan Konteks.")
        else:
            final_prompt = specific_prompt_template.format(input_text=input_text, rules_context=context)
            
            # Panggil API
            result = call_gemini_api(
                system_instruction=f"Anda adalah {action_type} Akademik tingkat Scopus Q1. Selalu patuhi Rules Context. Berikan output yang terstruktur dan mudah disalin.", 
                user_prompt=final_prompt
            )
            
            if result:
                st.session_state[f"{title}_result"] = result
                st.success("Analisis Selesai! Hasil ada di bawah.")

    # --- Bagian Hasil dan Copy-Paste ---
    if st.session_state.get(f"{title}_result"):
        st.subheader("🎉 Hasil Olahan Gemini (Siap Salin)")
        
        # Menggunakan st.text_area untuk hasil sehingga mudah dicopy-paste
        st.text_area(
            "Salin Teks Revisi/Template di Bawah:",
            st.session_state[f"{title}_result"],
            height=400,
            key=f"{title}_output_copy"
        )
        # st.markdown(st.session_state[f"{title}_result"]) # Bisa diganti dengan ini jika ingin format Markdown asli

# --- 3. Definisi Fungsi Spesifik (Prompt Templates, sama seperti sebelumnya) ---

def copy_editing_title_prompt():
    return """
    Tugas Anda adalah menganalisis dan mengoptimalkan JUDUL paper ini agar lebih berdampak, spesifik, dan sesuai SEO akademik.
    Gunakan Rules Context ({rules_context}) sebagai panduan.

    ### Judul Draft:
    {input_text}

    Tampilkan hasilnya dalam format 'Judul Asli' dan 'Judul Optimasi (Sertakan 3 Opsi Terbaik)'.
    """

def copy_editing_main_text_prompt():
    return """
    Tugas Anda adalah melakukan Copy Editing substantif pada Teks Utama. Fokus pada:
    1. Koherensi logis antar paragraf.
    2. Konsistensi argumentasi dan alur narasi akademik.
    3. Meningkatkan kepadatan informasi (conciseness).
    Gunakan Rules Context ({rules_context}) sebagai panduan.

    ### Teks Draft:
    {input_text}

    Tampilkan hasilnya dalam format 'Original Text' dan 'Suggested Logical Revisions'.
    """

def proofreading_grammar_prompt():
    return """
    Tugas Anda adalah melakukan Proofreading mendalam pada teks ini. Fokus pada:
    1. Tata Bahasa dan Ejaan (Grammar & Spelling) Bahasa Inggris Formal.
    2. Pilihan Kata agar lebih akademis (Academic Phrasing).
    3. Konsistensi istilah.
    Gunakan Rules Context ({rules_context}) sebagai panduan.

    ### Teks Draft:
    {input_text}

    Tampilkan hasilnya dalam format 'Original Text' dan 'Revised Text' (Gunakan Markdown bold untuk menyorot perubahan utama).
    """

def proofreading_reference_list_prompt():
    return """
    Tugas Anda adalah memvalidasi dan memformat Daftar Pustaka (Dapus) agar SANGAT SESUAI dengan Rules Context ({rules_context}).
    Fokus pada: Konsistensi gaya sitasi (misalnya, APA 7th, Vancouver, dll.), kapitalisasi, dan format tanggal.

    ### Daftar Pustaka Draft:
    {input_text}

    Tampilkan hasilnya dalam format 'Original List' dan 'Corrected and Formatted List'.
    """

def proofreading_acknowledgement_prompt():
    return """
    Tugas Anda adalah memeriksa dan memformat bagian Acknowledgement (Ucapan Terima Kasih) dan Lampiran. Fokus pada:
    1. Tone bahasa yang sesuai (formal dan sopan).
    2. Format penulisan nama institusi/sponsor.
    
    Gunakan Rules Context ({rules_context}).

    ### Teks Draft:
    {input_text}
    
    Tampilkan 'Original' dan 'Formatted Version'.
    """

def templating_abstract_prompt():
    return """
    Tugas Anda adalah menyusun ulang draft abstrak ini menjadi abstrak Scopus Q1 yang sangat PERSUASIF dan INFORMATIF.
    Terapkan struktur standar abstrak (Background, Method, Result, Conclusion) dan patuhi Rules Context ({rules_context}) (terutama batasan kata).

    ### Abstrak Draft:
    {input_text}

    Hasilkan output dalam template berikut:
    
    **Abstrak Optimasi:**
    **Keywords (3-5 kata kunci relevan):**
    """

def templating_imrad_prompt():
    return """
    Tugas Anda adalah menyusun teks draft ini ke dalam kerangka akademik IMRAD (Introduction, Method, Result, Discussion) atau mereorganisasi sub-bab yang diberikan.
    Fokus pada transisi yang mulus antar bagian dan kepatuhan terhadap Rules Context ({rules_context}).

    ### Teks Draft:
    {input_text}

    Hasilkan output yang terstruktur dengan judul sub-bab yang jelas dan deskripsi singkat mengapa struktur tersebut diubah.
    """


# --- 4. Struktur Menu Utama Streamlit (Routing) ---

st.set_page_config(
    page_title="Gemini Scopus Q1 Editor",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("✍️ Gemini Scopus Q1 Editor")
st.markdown("Aplikasi AI untuk menyempurnakan paper akademik sesuai standar publikasi jurnal kelas dunia.")

# --- Sidebar Menu ---
st.sidebar.title("🛠️ Fitur Editor")

# Pilihan Fitur Utama menggunakan Dropdown (Selectbox)
main_menu = st.sidebar.selectbox(
    "1. Pilih Fitur Utama:",
    ["Tentang Aplikasi", "Copy Editing (Substansi)", "Proofreading (Grammar/Format)", "Templating (Struktur)"]
)

# --- Sub-Menu Logika dan Routing ---

if main_menu == "Tentang Aplikasi":
    st.info("Selamat datang di Editor Scopus Q1. Gunakan menu samping untuk memilih layanan yang Anda butuhkan.")
    st.subheader("Prinsip Kerja:")
    st.markdown("Aplikasi ini menggunakan **Prompt Engineering** canggih untuk menginstruksikan Gemini 2.5 Flash agar bertindak sebagai editor Q1.")
    st.markdown(f"Model: **{MODEL}** (Dioptimalkan untuk kecepatan dan formalitas).")

elif main_menu == "Copy Editing (Substansi)":
    st.sidebar.subheader("2. Pilih Bagian Paper (Copy Editing)")
    sub_menu = st.sidebar.selectbox(
        "Fokus Substansi:",
        ["Judul", "Teks Utama (Intro, Metode, Dll)"]
    )
    rules_placeholder = "Gunakan bahasa yang padat, formal, dan fokus pada kebaruan penelitian (novelty)."

    if sub_menu == "Judul":
        render_content_page(
            "Copy Editing: Judul Paper",
            "Fokus pada kejelasan, dampak, dan relevansi Judul sesuai standar Q1.",
            "Copy Editor",
            rules_placeholder,
            copy_editing_title_prompt()
        )
    elif sub_menu == "Teks Utama (Intro, Metode, Dll)":
        render_content_page(
            "Copy Editing: Teks Utama",
            "Memastikan alur dan substansi argumentasi kuat dan koheren di seluruh paper.",
            "Copy Editor",
            rules_placeholder,
            copy_editing_main_text_prompt()
        )

elif main_menu == "Proofreading (Grammar/Format)":
    st.sidebar.subheader("2. Pilih Bagian Paper (Proofreading)")
    sub_menu = st.sidebar.selectbox(
        "Fokus Grammar/Format:",
        ["Tata Bahasa & Pilihan Kata", "Daftar Pustaka (Dapus)", "Acknowledgement & Lampiran"]
    )
    rules_placeholder = "Pastikan semua grammar Bahasa Inggris formal. Periksa konsistensi penggunaan huruf miring (italics) dan kapitalisasi."

    if sub_menu == "Tata Bahasa & Pilihan Kata":
        render_content_page(
            "Proofreading: Tata Bahasa & Pilihan Kata",
            "Koreksi ejaan, tata bahasa, dan tingkatkan formalitas kalimat Anda.",
            "Proofreader",
            rules_placeholder,
            proofreading_grammar_prompt()
        )
    elif sub_menu == "Daftar Pustaka (Dapus)":
        dapus_rules = "Terapkan gaya sitasi APA 7th ed. secara ketat. Perhatikan format DOI/URL dan kapitalisasi judul artikel."
        render_content_page(
            "Proofreading: Daftar Pustaka (Dapus)",
            "Memastikan Dapus Anda 100% sesuai dengan gaya sitasi yang diminta jurnal.",
            "Format Editor",
            dapus_rules,
            proofreading_reference_list_prompt()
        )
    elif sub_menu == "Acknowledgement & Lampiran":
        render_content_page(
            "Proofreading: Acknowledgement & Lampiran", 
            "Memastikan bagian pendukung paper Anda sesuai format formal.", 
            "Format Editor", 
            rules_placeholder, 
            proofreading_acknowledgement_prompt()
        )

elif main_menu == "Templating (Struktur)":
    st.sidebar.subheader("2. Pilih Struktur (Templating)")
    sub_menu = st.sidebar.selectbox(
        "Fokus Struktur:",
        ["Abstrak", "Struktur Penuh (IMRAD/Pendahuluan)"]
    )
    templating_rules = "Pastikan output sesuai batasan format penerbit. Abstrak harus 250 kata, menggunakan format: Background, Method, Result, Conclusion."

    if sub_menu == "Abstrak":
        render_content_page(
            "Templating: Abstrak",
            "Otomatis menyusun abstrak Anda ke dalam struktur Q1 yang persuasif dan terstruktur.",
            "Templating Specialist",
            templating_rules,
            templating_abstract_prompt()
        )
    elif sub_menu == "Struktur Penuh (IMRAD/Pendahuluan)":
        render_content_page(
            "Templating: Struktur Penuh (IMRAD)",
            "Susun ulang draft Anda ke dalam kerangka IMRAD standar jurnal Q1.",
            "Templating Specialist",
            templating_rules,
            templating_imrad_prompt()
        )
