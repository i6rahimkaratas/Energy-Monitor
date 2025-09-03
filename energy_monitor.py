import psutil
import time
import tkinter as tk
from tkinter import ttk
import threading
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

class EnerjiIzleyici:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Gerçek Zamanlı Enerji İzleyici")
        self.root.geometry("800x600")
        
        # Veri saklama listeleri
        self.zaman_verileri = []
        self.guc_verileri = []
        self.sarj_verileri = []
        self.max_veri_sayisi = 60  # Son 60 ölçümü sakla
        
        # Arayüz oluştur
        self.arayuz_olustur()
        
        # İzleme döngüsünü başlat
        self.izleme_aktif = True
        self.izleme_thread = threading.Thread(target=self.enerji_izle, daemon=True)
        self.izleme_thread.start()
        
    def arayuz_olustur(self):
        # Ana çerçeve
        ana_cerceve = ttk.Frame(self.root, padding="10")
        ana_cerceve.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Başlık
        baslik = ttk.Label(ana_cerceve, text="Enerji Tüketim İzleyici", 
                          font=("Arial", 16, "bold"))
        baslik.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Mevcut durum bilgileri
        durum_cerceve = ttk.LabelFrame(ana_cerceve, text="Mevcut Durum", padding="10")
        durum_cerceve.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Batarya yüzdesi
        ttk.Label(durum_cerceve, text="Batarya Seviyesi:").grid(row=0, column=0, sticky=tk.W)
        self.batarya_label = ttk.Label(durum_cerceve, text="---%", 
                                      font=("Arial", 12, "bold"))
        self.batarya_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        # Şarj durumu
        ttk.Label(durum_cerceve, text="Şarj Durumu:").grid(row=1, column=0, sticky=tk.W)
        self.sarj_durum_label = ttk.Label(durum_cerceve, text="---", 
                                         font=("Arial", 12))
        self.sarj_durum_label.grid(row=1, column=1, sticky=tk.W, padx=(10, 0))
        
        # Güç tüketimi
        ttk.Label(durum_cerceve, text="Anlık Güç Tüketimi:").grid(row=2, column=0, sticky=tk.W)
        self.guc_tuketim_label = ttk.Label(durum_cerceve, text="--- W", 
                                          font=("Arial", 12, "bold"))
        self.guc_tuketim_label.grid(row=2, column=1, sticky=tk.W, padx=(10, 0))
        
        # Kalan süre
        ttk.Label(durum_cerceve, text="Tahmini Kalan Süre:").grid(row=3, column=0, sticky=tk.W)
        self.kalan_sure_label = ttk.Label(durum_cerceve, text="---", 
                                         font=("Arial", 12))
        self.kalan_sure_label.grid(row=3, column=1, sticky=tk.W, padx=(10, 0))
        
        # Grafik alanı
        grafik_cerceve = ttk.LabelFrame(ana_cerceve, text="Güç Tüketim Grafiği", padding="10")
        grafik_cerceve.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        
        # Matplotlib figürü oluştur
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(8, 6), facecolor='white')
        self.fig.tight_layout(pad=3.0)
        
        # İlk grafik - Güç tüketimi
        self.ax1.set_title("Güç Tüketimi (W)")
        self.ax1.set_ylabel("Watt")
        self.line1, = self.ax1.plot([], [], 'b-', linewidth=2, label='Güç Tüketimi')
        self.ax1.grid(True, alpha=0.3)
        self.ax1.legend()
        
        # İkinci grafik - Batarya seviyesi
        self.ax2.set_title("Batarya Seviyesi (%)")
        self.ax2.set_ylabel("Yüzde")
        self.ax2.set_xlabel("Zaman (saniye)")
        self.line2, = self.ax2.plot([], [], 'g-', linewidth=2, label='Batarya')
        self.ax2.grid(True, alpha=0.3)
        self.ax2.legend()
        
        # Canvas oluştur ve yerleştir
        self.canvas = FigureCanvasTkAgg(self.fig, grafik_cerceve)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Grid yapılandırması
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        ana_cerceve.columnconfigure(1, weight=1)
        ana_cerceve.rowconfigure(2, weight=1)
        
    def batarya_bilgisi_al(self):
        """Batarya bilgilerini al"""
        try:
            batarya = psutil.sensors_battery()
            if batarya:
                return {
                    'yuzde': batarya.percent,
                    'sarj_oluyor': batarya.power_plugged,
                    'kalan_sure': batarya.secsleft if batarya.secsleft != psutil.POWER_TIME_UNLIMITED else None
                }
            else:
                # Masaüstü bilgisayar için tahmini değerler
                return {
                    'yuzde': 100,
                    'sarj_oluyor': True,
                    'kalan_sure': None
                }
        except Exception as e:
            print(f"Batarya bilgisi alınırken hata: {e}")
            return None
    
    def guc_tuketimi_hesapla(self):
        """CPU ve sistem yükü bazında güç tüketimi tahmini"""
        try:
            # CPU kullanım yüzdesi
            cpu_yuzde = psutil.cpu_percent(interval=0.1)
            
            # Bellek kullanımı
            bellek = psutil.virtual_memory()
            bellek_yuzde = bellek.percent
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            
            # Ağ I/O
            ag_io = psutil.net_io_counters()
            
            # Güç tüketimi tahmini (basitleştirilmiş model)
            # Temel sistem: 15W
            # CPU: 0-50W (kullanım yüzdesine göre)
            # RAM: 0-10W (kullanım yüzdesine göre)
            # Disk ve ağ için küçük ek maliyetler
            
            temel_guc = 15
            cpu_guc = (cpu_yuzde / 100) * 50
            bellek_guc = (bellek_yuzde / 100) * 10
            
            toplam_guc = temel_guc + cpu_guc + bellek_guc
            
            return {
                'toplam_guc': round(toplam_guc, 2),
                'cpu_yuzde': cpu_yuzde,
                'bellek_yuzde': bellek_yuzde,
                'cpu_guc': round(cpu_guc, 2)
            }
            
        except Exception as e:
            print(f"Güç hesaplanırken hata: {e}")
            return None
    
    def sure_formatla(self, saniye):
        """Saniyeyi saat:dakika:saniye formatına çevir"""
        if saniye is None or saniye < 0:
            return "Bilinmiyor"
        
        saat = saniye // 3600
        dakika = (saniye % 3600) // 60
        sn = saniye % 60
        
        if saat > 0:
            return f"{int(saat):02d}:{int(dakika):02d}:{int(sn):02d}"
        else:
            return f"{int(dakika):02d}:{int(sn):02d}"
    
    def grafikleri_guncelle(self):
        """Grafikleri güncelle"""
        if len(self.zaman_verileri) > 0:
            # Güç grafiği
            self.line1.set_data(self.zaman_verileri, self.guc_verileri)
            self.ax1.relim()
            self.ax1.autoscale_view()
            
            # Batarya grafiği
            self.line2.set_data(self.zaman_verileri, self.sarj_verileri)
            self.ax2.relim()
            self.ax2.autoscale_view()
            self.ax2.set_ylim(0, 100)
            
            # Canvas'ı güncelle
            self.canvas.draw()
    
    def enerji_izle(self):
        """Ana izleme döngüsü"""
        baslangic_zamani = time.time()
        
        while self.izleme_aktif:
            try:
                # Mevcut zamanı al
                gecen_zaman = time.time() - baslangic_zamani
                
                # Batarya bilgilerini al
                batarya_bilgi = self.batarya_bilgisi_al()
                
                # Güç tüketimi hesapla
                guc_bilgi = self.guc_tuketimi_hesapla()
                
                if batarya_bilgi and guc_bilgi:
                    # Verileri listelere ekle
                    self.zaman_verileri.append(gecen_zaman)
                    self.guc_verileri.append(guc_bilgi['toplam_guc'])
                    self.sarj_verileri.append(batarya_bilgi['yuzde'])
                    
                    # Veri sayısını sınırla
                    if len(self.zaman_verileri) > self.max_veri_sayisi:
                        self.zaman_verileri.pop(0)
                        self.guc_verileri.pop(0)
                        self.sarj_verileri.pop(0)
                    
                    # GUI'yi güncelle (ana thread'de)
                    self.root.after(0, self.gui_guncelle, batarya_bilgi, guc_bilgi)
                    
                    # Konsola yazdır
                    zaman_str = datetime.now().strftime("%H:%M:%S")
                    sarj_durum = "Şarj oluyor" if batarya_bilgi['sarj_oluyor'] else "Şarj olmuyor"
                    
                    print(f"[{zaman_str}] Batarya: {batarya_bilgi['yuzde']}% | "
                          f"Güç: {guc_bilgi['toplam_guc']}W | "
                          f"CPU: {guc_bilgi['cpu_yuzde']:.1f}% | "
                          f"Durum: {sarj_durum}")
                
                time.sleep(2)  # 2 saniyede bir güncelle
                
            except Exception as e:
                print(f"İzleme döngüsünde hata: {e}")
                time.sleep(2)
    
    def gui_guncelle(self, batarya_bilgi, guc_bilgi):
        """GUI elemanlarını güncelle"""
        try:
            # Batarya seviyesi
            batarya_renk = "red" if batarya_bilgi['yuzde'] < 20 else "orange" if batarya_bilgi['yuzde'] < 50 else "green"
            self.batarya_label.config(text=f"{batarya_bilgi['yuzde']}%", foreground=batarya_renk)
            
            # Şarj durumu
            if batarya_bilgi['sarj_oluyor']:
                self.sarj_durum_label.config(text="🔌 Şarj oluyor", foreground="green")
            else:
                self.sarj_durum_label.config(text="🔋 Batarya kullanıyor", foreground="orange")
            
            # Güç tüketimi
            guc_renk = "red" if guc_bilgi['toplam_guc'] > 60 else "orange" if guc_bilgi['toplam_guc'] > 30 else "green"
            self.guc_tuketim_label.config(text=f"{guc_bilgi['toplam_guc']} W", foreground=guc_renk)
            
            # Kalan süre
            if batarya_bilgi['kalan_sure']:
                kalan_sure_str = self.sure_formatla(batarya_bilgi['kalan_sure'])
                self.kalan_sure_label.config(text=kalan_sure_str)
            else:
                if batarya_bilgi['sarj_oluyor']:
                    self.kalan_sure_label.config(text="Şarj oluyor")
                else:
                    self.kalan_sure_label.config(text="Hesaplanıyor...")
            
            # Grafikleri güncelle
            self.grafikleri_guncelle()
            
        except Exception as e:
            print(f"GUI güncellenirken hata: {e}")
    
    def calistir(self):
        """Uygulamayı çalıştır"""
        try:
            print("Enerji İzleyici başlatılıyor...")
            print("Uygulama penceresi açılacak. Kapatmak için pencereyi kapatın.")
            print("-" * 60)
            
            # Pencere kapatma olayını yakala
            self.root.protocol("WM_DELETE_WINDOW", self.uygulamayi_kapat)
            
            # Ana döngüyü başlat
            self.root.mainloop()
            
        except KeyboardInterrupt:
            print("\nUygulama kullanıcı tarafından durduruldu.")
        except Exception as e:
            print(f"Uygulama çalıştırılırken hata: {e}")
        finally:
            self.izleme_aktif = False
    
    def uygulamayi_kapat(self):
        """Uygulamayı güvenli şekilde kapat"""
        self.izleme_aktif = False
        self.root.quit()
        self.root.destroy()

# Uygulamayı başlat
if __name__ == "__main__":
    try:
        izleyici = EnerjiIzleyici()
        izleyici.calistir()
    except Exception as e:
        print(f"Program başlatılırken hata: {e}")
        print("Gerekli kütüphanelerin yüklü olduğundan emin olun:")
        print("pip install psutil matplotlib tkinter")