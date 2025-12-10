import streamlit as st
import io
import time
from google import genai
from google.genai import types

# --- 0. Setup Klien Gemini & Konfigurasi ---

# Pastikan API Key ada di st.secrets["gemini_api_key"]
try:
    API_KEY = st.secrets["gemini_api_key"]
except KeyError:
    st.error("Kunci API Gemini tidak ditemukan. Harap masukkan API key Anda di file .streamlit/secrets.toml atau di Streamlit Cloud Secrets.")
    st.stop()

client = genai.Client(api_key=API_KEY)
MODEL_FLASH = 'gemini-2.5-flash'
MODEL_PRO = 'gemini-2.5-pro' 
TEMPERATURE = 0.3

# --- 1. Fungsi Inti: Panggilan Model Gemini ---

def call_gemini_api(system_instruction, user_prompt, model_choice=MODEL_FLASH, file_parts=None):
    """
    Fungsi utilitas untuk memanggil Gemini API, mendukung input multimodal.
    """
    contents = [user_prompt]
    if file_parts:
        contents.extend(file_parts)
    
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=TEMPERATURE
    )

    with st.spinner(f"Memproses dengan Gemini Editor ({model_choice})..."):
        try:
            response = client.models.generate_content(
                model=model_choice,
                contents=contents,
                config=config
            )
            return response.text
        except Exception as e:
            # Menonaktifkan tool_config jika terjadi error spesifik
            st.error(f"Terjadi kesalahan saat memanggil API: {e}")
            return None

# --- 2. Fungsi Ekstraksi Aturan Format dari File ---

def extract_rules_from_file(uploaded_file):
    """
    Mengekstrak aturan format dari TXT atau gambar (JPG/PNG).
    """
    file_type = uploaded_file.type
    
    if file_type == "text/plain":
        stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
        return stringio.read()
    
    elif file_type in ["image/jpeg", "image/png"]:
        # Upload gambar ke Gemini API
        image_part = types.Part.from_bytes(
            data=uploaded_file.getvalue(),
            mime_type=file_type
        )
        
        prompt = "Ekstrak semua aturan format, gaya sitasi, dan batasan kata yang terlihat jelas dari gambar ini. Format outputnya sebagai daftar yang jelas."
        
        st.info("Mengambil aturan format dari gambar (Menggunakan Gemini 2.5 Pro)...")
        rules_text = call_gemini_api(
            system_instruction="Anda adalah spesialis ekstraksi data dari format jurnal Scopus Q1.",
            user_prompt=prompt,
            model_choice=MODEL_PRO,
            file_parts=[image_part]
        )
        return rules_text if rules_text else "Gagal mengekstrak aturan dari gambar."

    elif file_type == "application/pdf":
        st.warning("Ekstraksi PDF kompleks. Silakan salin teks aturan dari PDF secara manual atau unggah sebagai file gambar.")
        return None
    
    else:
        st.error(f"Tipe file '{file_type}' tidak didukung.")
        return None


# --- 3. Template Halaman Universal (Proofreading & Templating) ---

def render_content_page(title, instructions, action_type, rules_context_placeholder, specific_prompt_template, model_to_use=MODEL_FLASH):
    """
    Template Halaman dengan Upload Format dan Download Hasil.
    """
    st.header(title)
    st.markdown(instructions)

    # --- INPUT RULES / CONTEXT ---
    st.subheader("1. Aturan Konteks Jurnal")
    
    rule_source = st.radio(
        "Pilih Sumber Aturan Format:",
        ("Teks Manual", "Upload File (.txt, .jpg, .png)"),
        key=f"{title}_source"
    )

    context = ""
    uploaded_file = None
    if rule_source == "Teks Manual":
        context = st.text_area(
            "Masukkan aturan jurnal (e.g., gaya sitasi, batasan kata, formalitas):",
            value=rules_context_placeholder,
            height=100,
            key=f"{title}_context"
        )
    else: # Upload File
        uploaded_file = st.file_uploader(
            "Upload file aturan format (.txt, .jpg, atau .png):",
            type=["txt", "jpg", "jpeg", "png"],
            key=f"{title}_uploader"
        )
        if uploaded_file is not None:
            context = extract_rules_from_file(uploaded_file)
            if context:
                st.info("Aturan Format yang Diekstrak (Sebagian Tampil):")
                st.text(context[:500] + "...") 
    
    if not context:
        st.warning("Harap masukkan atau unggah Aturan Konteks.")
        
    st.subheader("2. Teks Draft")
    input_text = st.text_area("Masukkan teks yang akan diproses:", height=300, key=f"{title}_input")

    if f"{title}_result" not in st.session_state:
        st.session_state[f"{title}_result"] = ""

    if st.button(f"Jalankan {action_type}", type="primary"):
        if not input_text or not context:
            st.warning("Mohon masukkan teks draft dan Aturan Konteks.")
        else:
            final_prompt = specific_prompt_template.format(input_text=input_text, rules_context=context)
            
            result = call_gemini_api(
                system_instruction=f"Anda adalah {action_type} Akademik tingkat Scopus Q1. Selalu patuhi Rules Context.", 
                user_prompt=final_prompt,
                model_choice=model_to_use
            )
            
            if result:
                st.session_state[f"{title}_result"] = result
                st.success("Analisis Selesai! Hasil ada di bawah.")

    # --- Bagian Hasil, Copy-Paste, dan Download ---
    result_text = st.session_state.get(f"{title}_result")
    
    if result_text:
        st.subheader("🎉 Hasil Olahan Gemini (Siap Salin & Download)")
        
        # 1. Fitur Copy-Paste
        st.text_area(
            "Salin Teks Revisi/Template di Bawah:",
            result_text,
            height=400,
            key=f"{title}_output_copy"
        )

        # 2. Fitur Download (.txt)
        st.download_button(
            label="⬇️ Download Hasil (.txt)",
            data=result_text.encode('utf-8'),
            file_name=f"{title.replace(': ', '_').lower()}_revisi.txt",
            mime="text/plain"
        )

# --- 4. Fungsi Copy Editing Chat Interaktif (Fitur Baru) ---

def copy_editing_chat_page():
    st.header("💬 Copy Editing Interaktif (Analisis Substansi)")
    st.markdown("Diskusikan alur argumentasi, sitasi, dan relevansi substansi paper Anda dengan AI. Model ini mensimulasikan pemeriksaan Scopus Q1.")

    # --- 1. Aturan Konteks (Diambil dari Input Teks) ---
    rules_placeholder = st.text_area(
        "Masukkan Aturan Konteks Jurnal dan/atau Informasi Sitasi/Jurnal yang Ingin Dicek (Wajib):",
        value="Contoh: Jurnal target saya adalah 'Journal of Applied Sciences' (Scopus Q1, H-Index 90). Kami harus mengutip 50% sumber dari 5 tahun terakhir.",
        height=100,
        key="chat_rules_input"
    )
    
    if not rules_placeholder:
        st.warning("Mohon masukkan Aturan Konteks untuk memulai diskusi.")
        return 

    # --- 2. Setup Chat Session State ---
    
    LAST_RULES_KEY = "last_rules_used" 
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    # LOGIKA UTAMA RESET/INISIALISASI:
    rules_changed = (st.session_state.get(LAST_RULES_KEY) != rules_placeholder)
    
    if "chat_service" not in st.session_state or rules_changed:
        
        # 1. Definisikan System Instruction yang baru
        system_instruction = f"""
        Anda adalah Pembimbing Akademik dan Editor Jurnal Scopus Q1.
        Tugas Anda adalah berdiskusi dengan penulis mengenai substansi, kebaruan (novelty), dan strategi sitasi paper mereka.
        Anda harus:
        1. Selalu mengacu pada RULES CONTEXT: "{rules_placeholder}".
        2. Mensimulasikan pemeriksaan sitasi dan ketersediaan jurnal di Scopus/Scimago berdasarkan konteks yang diberikan.
        3. Beri saran yang kritis dan membangun terkait alur argumentasi, bahasa, dan metodologi.
        4. Gunakan bahasa yang formal dan profesional.
        """
        
        # 2. Buat objek chat service baru (Fix untuk TypeError)
        try:
            st.session_state.chat_service = client.chats.create(
                model=MODEL_PRO, 
                system_instruction=system_instruction
            )
            # 3. Update state dan pesan sambutan
            st.session_state[LAST_RULES_KEY] = rules_placeholder
            st.session_state.messages = [] 
            st.session_state.messages.append(
                {"role": "model", "content": f"Selamat datang! Sesi baru diinisialisasi. **Berdasarkan konteks Anda, apa bagian paper (Intro, Metode, Dll) yang ingin kita bahas terlebih dahulu?**"}
            )
            st.info("Sesi Chat diinisialisasi ulang dengan Aturan Konteks yang baru.")
            
        except Exception as e:
            st.error(f"Gagal menginisialisasi Chat Service. Pastikan API Key valid dan Model {MODEL_PRO} tersedia. Error: {e}")
            return


    # --- 3. Tampilkan Riwayat Chat ---
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- 4. Input Pengguna (Chat) ---
    # Disabled jika chat service belum berhasil dibuat
    if prompt := st.chat_input("Tanyakan tentang paper Anda atau kirim draf paragraf:", disabled=("chat_service" not in st.session_state)):
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        try:
            response = st.session_state.chat_service.send_message(prompt)
            
            with st.chat_message("model"):
                st.markdown(response.text)
            st.session_state.messages.append({"role": "model", "content": response.text})
            
        except Exception as e:
            st.error(f"Terjadi kesalahan saat mengirim pesan: {e}")
            st.session_state.pop("chat_service", None)
            st.session_state.messages = []
            st.warning("Sesi chat terputus. Silakan coba kembali atau refresh halaman.")

# --- 5. Definisi Prompt Templates (Sama seperti sebelumnya) ---

def copy_editing_title_prompt():
    return """
    Tugas Anda adalah menganalisis dan mengoptimalkan JUDUL paper ini agar lebih berdampak, spesifik, dan sesuai SEO akademik.
    Gunakan Rules Context ({rules_context}) sebagai panduan.

    ### Judul Draft:
    {input_text}

    Tampilkan hasilnya dalam format 'Judul Asli' dan 'Judul Optimasi (Sertakan 3 Opsi Terbaik)'.
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


# --- 6. Struktur Menu Utama Streamlit (Routing) ---

# Pengaturan Global
st.set_page_config(
    page_title="Gemini Scopus Q1 Editor",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("✍️ Gemini Scopus Q1 Editor")
st.markdown("Aplikasi AI untuk menyempurnakan paper akademik sesuai standar publikasi jurnal kelas dunia.")

# --- Sidebar Menu ---
st.sidebar.title("🛠️ Fitur Editor")

main_menu = st.sidebar.selectbox(
    "1. Pilih Fitur Utama:",
    ["Tentang Aplikasi", "Copy Editing (Substansi)", "Proofreading (Grammar/Format)", "Templating (Struktur)"]
)

# --- Routing Logika Berdasarkan Pilihan Menu ---

if main_menu == "Tentang Aplikasi":
    st.info("Selamat datang di Editor Scopus Q1. Gunakan menu samping untuk memilih layanan yang Anda butuhkan.")
    st.subheader("Prinsip Kerja:")
    st.markdown("Aplikasi ini menggunakan **Prompt Engineering** canggih untuk menginstruksikan Gemini 2.5 Flash/Pro agar bertindak sebagai editor Q1.")
    st.markdown(f"Model Dasar: **{MODEL_FLASH}**")
    st.markdown(f"Model untuk Analisis Substansi/Diskusi: **{MODEL_PRO}**")

elif main_menu == "Copy Editing (Substansi)":
    st.sidebar.subheader("2. Pilih Mode Analisis")
    sub_menu = st.sidebar.selectbox(
        "Fokus Substansi:",
        ["Diskusi Interaktif (Chat)", "Judul (Analisis Sekali Jalan)"]
    )
    
    if sub_menu == "Diskusi Interaktif (Chat)":
        copy_editing_chat_page()
    elif sub_menu == "Judul (Analisis Sekali Jalan)":
        rules_placeholder = "Gunakan bahasa yang padat, formal, dan fokus pada kebaruan penelitian (novelty)."
        render_content_page(
            "Copy Editing: Judul Paper",
            "Fokus pada kejelasan, dampak, dan relevansi Judul sesuai standar Q1.",
            "Copy Editor",
            rules_placeholder,
            copy_editing_title_prompt(),
            model_to_use=MODEL_PRO 
        )

elif main_menu == "Proofreading (Grammar/Format)":
    st.sidebar.subheader("2. Pilih Bagian Paper (Proofreading)")
    sub_menu = st.sidebar.selectbox(
        "Fokus Grammar/Format:",
        ["Tata Bahasa & Pilihan Kata", "Daftar Pustaka (Dapus)", "Acknowledgement & Lampiran"]
    )
    rules_placeholder = "Pastikan semua grammar Bahasa Inggris formal dan hindari kalimat pasif."

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
            templating_abstract_prompt(),
            model_to_use=MODEL_PRO
        )
    elif sub_menu == "Struktur Penuh (IMRAD/Pendahuluan)":
        render_content_page(
            "Templating: Struktur Penuh (IMRAD)",
            "Susun ulang draft Anda ke dalam kerangka IMRAD standar jurnal Q1.",
            "Templating Specialist",
            templating_rules,
            templating_imrad_prompt(),
            model_to_use=MODEL_PRO
        )
