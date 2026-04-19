import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, 
  Mic, 
  LogOut, 
  User, 
  Cpu, 
  Volume2, 
  Mic2, 
  Settings, 
  ChevronRight,
  Sparkles,
  Loader2,
  X,
  Palette,
  MessageSquare,
  Zap,
  Globe
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

// Types
interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: number;
}

type AccentColor = 'blue' | 'purple' | 'emerald' | 'rose' | 'amber';
type Personality = 'Professional' | 'Friendly' | 'Creative';

export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [username, setUsername] = useState<string | null>(null);
  const [view, setView] = useState<'login' | 'register' | 'register_email'>('login');
  const [messages, setMessages] = useState<Message[]>([
    { id: '1', text: 'Hallo! Ich bin Nerio. Wie kann ich dir heute helfen?', sender: 'bot', timestamp: Date.now() }
  ]);
  const [input, setInput] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(false);
  const [sttEnabled, setSttEnabled] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [language, setLanguage] = useState<string>('de');
  
  // Audio Mode: 'browser' or 'server'
  const [ttsMode, setTtsMode] = useState<'browser' | 'server'>('server');
  
  // Creative Settings
  const [accentColor, setAccentColor] = useState<AccentColor>('emerald');
  const [personality, setPersonality] = useState<Personality>('Friendly');
  const [isCompact, setIsCompact] = useState(false);
  const [isRecording, setIsRecording] = useState(false);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const holdTimerRef = useRef<NodeJS.Timeout | null>(null);
  const isHoldingRef = useRef(false);

  // Check session on mount
  useEffect(() => {
    // Check if we are on the register_email page
    if (window.location.pathname.includes('register_email')) {
      setView('register_email');
    }

    const checkAuth = async () => {
      try {
        const res = await fetch('/get_username');
        if (res.ok) {
          const contentType = res.headers.get("content-type");
          if (contentType && contentType.includes("application/json")) {
            const data = await res.json();
            if (data.username) {
              setUsername(data.username);
              setIsLoggedIn(true);
              if (data.language) setLanguage(data.language);
            }
          }
        }
      } catch (err) {
        console.error("Auth check failed", err);
      }
    };
    checkAuth();
  }, []);

  const handleLanguageChange = async (lang: string) => {
    setLanguage(lang);
    try {
      await fetch('/api/save_language', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language: lang })
      });
    } catch (e) {
      console.error("Failed to save language", e);
    }
  };

  // Audio Model Listener (Wake Word)
  useEffect(() => {
    if (!isLoggedIn || !sttEnabled) return;

    let recognizer: any;
    const MODEL_URL = `${window.location.origin}/static/audio-model/model/`;

    const startAudioListener = async () => {
      try {
        const sc = (window as any).speechCommands;
        if (!sc) return;

        recognizer = sc.create(
          "BROWSER_FFT",
          undefined,
          MODEL_URL + "model.json",
          MODEL_URL + "metadata.json"
        );
        await recognizer.ensureModelLoaded();
        
        const classLabels = recognizer.wordLabels();

        recognizer.listen(async (result: any) => {
          const scores = result.scores;
          
          // Trigger: scores[1] > 0.95
          if (scores[1] > 0.95 && !isRecording && sttEnabled) {
            console.log("🎙 Wake word detected!");
            startRecording();
          }
        }, {
          includeSpectrogram: true,
          probabilityThreshold: 0.0,
          invokeCallbackOnNoiseAndUnknown: true,
          overlapFactor: 0.5
        });
      } catch (err) {
        console.error("Audio listener failed", err);
      }
    };

    startAudioListener();

    return () => {
      if (recognizer && recognizer.isListening()) {
        recognizer.stopListening();
      }
    };
  }, [isLoggedIn, sttEnabled, isRecording]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // Send personality (mode) to server when changed
  useEffect(() => {
    if (!isLoggedIn) return;
    
    const updateModi = async () => {
      try {
        await fetch('/modi', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ modi: personality })
        });
        console.log("Modi updated on server:", personality);
      } catch (err) {
        console.error("Failed to update modi on server", err);
      }
    };
    
    updateModi();
  }, [personality, isLoggedIn]);

  const accentColors: Record<AccentColor, string> = {
    blue: 'bg-blue-600 shadow-blue-600/20 text-blue-400 border-blue-500/30',
    purple: 'bg-purple-600 shadow-purple-600/20 text-purple-400 border-purple-500/30',
    emerald: 'bg-emerald-600 shadow-emerald-600/20 text-emerald-400 border-emerald-500/30',
    rose: 'bg-rose-600 shadow-rose-600/20 text-rose-400 border-rose-500/30',
    amber: 'bg-amber-600 shadow-amber-600/20 text-amber-400 border-amber-500/30',
  };

  const getAccentClass = (type: 'bg' | 'text' | 'border' | 'shadow') => {
    const color = accentColors[accentColor];
    if (type === 'bg') return color.split(' ')[0];
    if (type === 'shadow') return color.split(' ')[1];
    if (type === 'text') return color.split(' ')[2];
    if (type === 'border') return color.split(' ')[3];
    return '';
  };

  const playAudioSequentially = async (audioFiles: string[]) => {
    for (const audioPath of audioFiles) {
      if (audioPath && audioPath !== '0') {
        const audio = new Audio(audioPath);
        await new Promise((resolve) => {
          audio.onended = resolve;
          audio.onerror = resolve;
          audio.play().catch(err => {
            console.error("Audio playback error", err);
            resolve(null);
          });
        });
      }
    }
  };

  const speakWithBrowser = (text: string) => {
    if (!ttsEnabled) return;
    // Cancel any ongoing speech
    window.speechSynthesis.cancel();
    
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'de-DE';
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    
    // Select a nice voice if available
    const voices = window.speechSynthesis.getVoices();
    const germanVoice = voices.find(v => v.lang.startsWith('de'));
    if (germanVoice) utterance.voice = germanVoice;
    
    window.speechSynthesis.speak(utterance);
  };

  const handleSendMessage = async (textOverride?: string) => {
    const messageText = textOverride || input;
    if (!messageText.trim()) return;
    
    const userMsg: Message = {
      id: Date.now().toString(),
      text: messageText,
      sender: 'user',
      timestamp: Date.now()
    };
    
    setMessages(prev => [...prev, userMsg]);
    if (!textOverride) setInput('');
    setIsTyping(true);

    try {
      // We prepend the personality instruction to the message so the agent knows the mode
      // without changing app.py
      const personalityPrompt = personality === 'Creative' 
        ? "[System: Antworte kreativ, inspirierend und nutze Emojis] " 
        : personality === 'Professional' 
        ? "[System: Antworte sachlich, präzise und professionell] " 
        : "[System: Antworte freundlich und hilfsbereit] ";

      const response = await fetch('/nerio_chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: personalityPrompt + messageText, 
          switch: ttsEnabled 
        })
      });

      const data = await response.json();
      const responseText = data.responses.map((r: string) => r.trim() + ".").join(" ");
      
      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        text: responseText,
        sender: 'bot',
        timestamp: Date.now()
      };
      setMessages(prev => [...prev, botMsg]);
      
      if (ttsEnabled) {
        if (ttsMode === 'server' && data.audio && data.audio.length > 0) {
          await playAudioSequentially(data.audio);
        } else if (ttsMode === 'browser') {
          speakWithBrowser(responseText);
        }
      }
    } catch (err) {
      console.error("Chat error", err);
    } finally {
      setIsTyping(false);
    }
  };

  const startRecording = async (timeout: number | null = 5000) => {
    if (isRecording) return;
    setIsRecording(true);
    setIsListening(true);
    document.body.classList.add("voice-active");
    
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        document.body.classList.remove("voice-active");
        if (recordingTimeoutRef.current) {
          clearTimeout(recordingTimeoutRef.current);
          recordingTimeoutRef.current = null;
        }
        
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const formData = new FormData();
        formData.append('file', audioBlob, 'recording.webm');

        try {
          const res = await fetch('/stt', { method: 'POST', body: formData });
          const data = await res.json();
          if (data.transcript && data.transcript.trim()) {
            handleSendMessage(data.transcript.trim());
          }
        } catch (err) {
          console.error("STT error", err);
        }
        setIsListening(false);
        setIsRecording(false);
      };

      mediaRecorder.start();
      
      if (timeout !== null) {
        recordingTimeoutRef.current = setTimeout(() => {
          if (mediaRecorder.state === 'recording') {
            mediaRecorder.stop();
          }
        }, timeout);
      }

    } catch (err) {
      console.error("Microphone access denied", err);
      setIsListening(false);
      setIsRecording(false);
      document.body.classList.remove("voice-active");
    }
  };

  const toggleListening = () => {
    if (isListening) {
      mediaRecorderRef.current?.stop();
    } else {
      startRecording(5000);
    }
  };

  const handleMicMouseDown = () => {
    isHoldingRef.current = false;
    holdTimerRef.current = setTimeout(() => {
      isHoldingRef.current = true;
      if (!isListening) {
        startRecording(null); // Record without timeout
      }
    }, 400); // 400ms to detect hold
  };

  const handleMicMouseUp = () => {
    if (holdTimerRef.current) {
      clearTimeout(holdTimerRef.current);
      holdTimerRef.current = null;
    }
    
    if (isHoldingRef.current && isListening) {
      mediaRecorderRef.current?.stop();
    }
  };

  const handleRegisterEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const form = e.target as HTMLFormElement;
    const formData = new FormData(form);

    try {
      const res = await fetch('/register_email', {
        method: 'POST',
        body: new URLSearchParams(formData as any),
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });

      if (res.ok) {
        window.history.pushState({}, '', '/');
        setView('login');
        const userRes = await fetch('/get_username');
        if (userRes.ok) {
          const userData = await userRes.json();
          if (userData.username) {
            setUsername(userData.username);
            setIsLoggedIn(true);
          }
        }
      } else {
        const text = await res.text();
        setError(text || "Fehler beim Speichern der E-Mail-Einstellungen");
      }
    } catch (err) {
      setError("Verbindung zum Server fehlgeschlagen");
    }
  };

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const form = e.target as HTMLFormElement;
    const formData = new FormData(form);

    const endpoint = view === 'login' ? '/' : '/register';
    
    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        body: new URLSearchParams(formData as any),
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        redirect: 'follow'
      });

      console.log("Auth response URL:", res.url);
      console.log("Auth response status:", res.status);
      console.log("Auth response redirected:", res.redirected);

      // Check if the final URL is /register_email (case-insensitive and robust)
      if (res.url.toLowerCase().includes('register_email')) {
        console.log("Redirecting to register_email via view state...");
        window.history.pushState({}, '', '/register_email');
        setView('register_email');
        return;
      }

      if (res.ok) {
        // Fallback: If it's a registration and we are still here, maybe the redirect didn't happen in the URL
        // but the server intended it. We can check the response text or just try to get username.
        const text = await res.text();
        if (view === 'register' && text.toLowerCase().includes('email')) {
           window.history.pushState({}, '', '/register_email');
           setView('register_email');
           return;
        }

        // Success - check if we are logged in
        const userRes = await fetch('/get_username');
        if (userRes.ok) {
          const userData = await userRes.json();
          if (userData.username) {
            setUsername(userData.username);
            setIsLoggedIn(true);
            return;
          }
        }
      }
      
      // If not ok or no username, show error
      const text = await res.text();
      setError(text || "Fehler bei der Authentifizierung");
    } catch (err) {
      setError("Verbindung zum Server fehlgeschlagen");
    }
  };

  const handleLogout = async () => {
    await fetch('/logout');
    setIsLoggedIn(false);
    setUsername(null);
  };

  if (!isLoggedIn) {
    if (view === 'register_email') {
      return (
        <div className="min-h-screen flex items-center justify-center p-4 overflow-y-auto bg-slate-950">
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full max-w-md bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-8 my-8 shadow-2xl"
          >
            <div className="flex justify-center mb-6">
              <div className="w-16 h-16 bg-emerald-500/20 rounded-2xl flex items-center justify-center border border-emerald-500/30">
                <Zap className="w-8 h-8 text-emerald-400" />
              </div>
            </div>
            
            <h2 className="text-3xl font-bold text-center mb-2 tracking-tight text-white">
              E-Mail Einstellungen
            </h2>
            <p className="text-white/50 text-center mb-8">
              Konfiguriere deine E-Mail und Loxone Anbindung.
            </p>

            {error && (
              <div className="bg-rose-500/20 border border-rose-500/50 text-rose-200 px-4 py-3 rounded-2xl mb-6 text-sm flex items-center gap-3">
                <X className="w-4 h-4 flex-shrink-0" />
                {error}
              </div>
            )}

            <form onSubmit={handleRegisterEmail} className="space-y-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-white/50 ml-1 uppercase tracking-wider">E-Mail-Konto</label>
                <input type="text" name="email" placeholder="E-Mail-Adresse (optional)" className="w-full px-5 py-4 bg-white/5 border border-white/10 rounded-2xl text-white placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all" />
                <input type="password" name="email_password" placeholder="E-Mail-Passwort (optional)" className="w-full px-5 py-4 bg-white/5 border border-white/10 rounded-2xl text-white placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all" />
              </div>

              <div className="grid grid-cols-3 gap-2">
                <div className="col-span-2">
                  <label className="text-xs font-medium text-white/50 ml-1 uppercase tracking-wider">IMAP-Server</label>
                  <input type="text" name="imap_server" placeholder="z.B. imap.gmail.com" className="w-full px-5 py-4 bg-white/5 border border-white/10 rounded-2xl text-white placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all" />
                </div>
                <div>
                  <label className="text-xs font-medium text-white/50 ml-1 uppercase tracking-wider">Port</label>
                  <input type="number" name="imap_port" placeholder="993" defaultValue="993" className="w-full px-5 py-4 bg-white/5 border border-white/10 rounded-2xl text-white placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all" />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2">
                <div className="col-span-2">
                  <label className="text-xs font-medium text-white/50 ml-1 uppercase tracking-wider">SMTP-Server</label>
                  <input type="text" name="smtp_server" placeholder="z.B. smtp.gmail.com" className="w-full px-5 py-4 bg-white/5 border border-white/10 rounded-2xl text-white placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all" />
                </div>
                <div>
                  <label className="text-xs font-medium text-white/50 ml-1 uppercase tracking-wider">Port</label>
                  <input type="number" name="smtp_port" placeholder="465" defaultValue="465" className="w-full px-5 py-4 bg-white/5 border border-white/10 rounded-2xl text-white placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all" />
                </div>
              </div>

              <div className="space-y-1 pt-2">
                <label className="text-xs font-medium text-white/50 ml-1 uppercase tracking-wider">Loxone Anbindung</label>
                <input type="text" name="loxone_ip" placeholder="Loxone IP-Adresse (optional)" className="w-full px-5 py-4 bg-white/5 border border-white/10 rounded-2xl text-white placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all" />
                <input type="text" name="loxone_user" placeholder="Loxone Benutzername (optional)" className="w-full px-5 py-4 bg-white/5 border border-white/10 rounded-2xl text-white placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all" />
                <input type="password" name="loxone_pass" placeholder="Loxone Passwort (optional)" className="w-full px-5 py-4 bg-white/5 border border-white/10 rounded-2xl text-white placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all" />
              </div>

              <button 
                type="submit"
                className="w-full py-4 bg-emerald-500 hover:bg-emerald-600 text-white rounded-2xl font-semibold shadow-lg shadow-emerald-500/20 transition-all mt-4"
              >
                Registrierung abschließen
              </button>
              
              <button 
                type="button"
                onClick={() => {
                  window.history.pushState({}, '', '/');
                  setView('login');
                }}
                className="w-full py-4 bg-white/5 hover:bg-white/10 text-white/70 rounded-2xl font-medium transition-all"
              >
                Abbrechen
              </button>
            </form>
          </motion.div>
        </div>
      );
    }

    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass p-8 rounded-3xl w-full max-w-md shadow-2xl"
        >
          <div className="flex justify-center mb-6">
            <div className={`w-16 h-16 rounded-2xl flex items-center justify-center border ${getAccentClass('bg').replace('bg-', 'bg-')}/20 ${getAccentClass('border')}`}>
              <Sparkles className={`${getAccentClass('text')} w-8 h-8`} />
            </div>
          </div>
          
          <h2 className="text-3xl font-bold text-center mb-2 tracking-tight">
            {view === 'login' ? 'Willkommen zurück' : 'Konto erstellen'}
          </h2>
          <p className="text-white/50 text-center mb-8">
            {view === 'login' ? 'Melde dich an, um mit Nerio zu chatten.' : 'Starte deine Reise mit Nerio AI.'}
          </p>

          <form onSubmit={handleAuth} className="space-y-4">
            {view === 'register' && (
              <input 
                name="code"
                type="text" 
                placeholder="Registrierungscode" 
                required
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-white/20 transition-all"
              />
            )}
            <input 
              name="username"
              type="text" 
              placeholder="Benutzername" 
              required
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-white/20 transition-all"
            />
            <input 
              name="password"
              type="password" 
              placeholder="Passwort" 
              required
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-white/20 transition-all"
            />
            
            {error && <p className="text-red-400 text-xs text-center">{error}</p>}

            <button 
              type="submit"
              className={`w-full ${getAccentClass('bg')} hover:opacity-90 text-white font-semibold py-3 rounded-xl transition-all shadow-lg ${getAccentClass('shadow')} flex items-center justify-center gap-2 group`}
            >
              {view === 'login' ? 'Einloggen' : 'Registrieren'}
              <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>
          </form>

          <div className="mt-8 text-center">
            <button 
              onClick={() => { setView(view === 'login' ? 'register' : 'login'); setError(null); }}
              className={`${getAccentClass('text')} hover:opacity-80 text-sm font-medium transition-colors`}
            >
              {view === 'login' ? 'Noch kein Konto? Jetzt registrieren' : 'Bereits ein Konto? Zum Login'}
            </button>
          </div>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      {/* Unified Chat Container */}
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className={`glass rounded-[2.5rem] w-full max-w-4xl h-[85vh] flex relative overflow-hidden transition-all duration-500 ${isListening ? 'glow-gold ring-2 ring-yellow-500/50' : ''}`}
      >
        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Chat Header */}
          <div className="p-6 border-b border-white/10 flex items-center justify-between bg-white/5">
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className={`w-10 h-10 ${getAccentClass('bg')} rounded-full flex items-center justify-center shadow-lg ${getAccentClass('shadow')}`}>
                  <Cpu className="text-white w-5 h-5" />
                </div>
                <div className="absolute bottom-0 right-0 w-3 h-3 bg-green-500 border-2 border-[#0a0a0a] rounded-full" />
              </div>
              <div>
                <h3 className="font-bold">Nerio Assistant</h3>
                <p className="text-xs text-white/50">{username} • {personality} Mode</p>
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              <button 
                onClick={() => setShowSettings(!showSettings)}
                className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all ${showSettings ? 'bg-white/20 text-white' : 'text-white/40 hover:bg-white/10 hover:text-white'}`}
              >
                <Settings className="w-5 h-5" />
              </button>
              <button 
                onClick={handleLogout}
                className="w-10 h-10 rounded-xl flex items-center justify-center text-white/40 hover:bg-red-500/10 hover:text-red-400 transition-all"
              >
                <LogOut className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className={`flex-1 overflow-y-auto p-6 space-y-6 ${isCompact ? 'space-y-3' : 'space-y-6'}`}>
            <AnimatePresence initial={false}>
              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  className={`flex items-start gap-3 ${msg.sender === 'user' ? 'flex-row-reverse' : ''}`}
                >
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 overflow-hidden ${msg.sender === 'user' ? 'bg-white/10' : getAccentClass('bg')}`}>
                    {msg.sender === 'user' ? (
                      <img src="/static/user.png" alt="User" className="w-full h-full object-cover" referrerPolicy="no-referrer" />
                    ) : (
                      <img src="/static/nerio.png" alt="Nerio" className="w-full h-full object-cover" referrerPolicy="no-referrer" />
                    )}
                  </div>
                  <div className={`max-w-[80%] p-4 rounded-2xl shadow-sm ${
                    msg.sender === 'user' 
                      ? 'bg-white/10 rounded-tr-none' 
                      : `${getAccentClass('bg')}/20 border ${getAccentClass('border')} rounded-tl-none`
                  } ${isCompact ? 'p-3' : 'p-4'}`}>
                    <p className={`text-sm leading-relaxed ${isCompact ? 'text-xs' : 'text-sm'}`}>{msg.text}</p>
                    <span className="text-[10px] text-white/30 mt-2 block">
                      {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
            
            {isTyping && (
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center gap-2 text-white/30 ml-11"
              >
                <Loader2 className="w-3 h-3 animate-spin" />
                <span className="text-xs">Nerio denkt nach...</span>
              </motion.div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Input Area */}
          <div className="p-6 bg-white/5 border-t border-white/10">
            <div className="flex items-center gap-3">
              <div className="relative flex-1">
                <input 
                  type="text" 
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                  placeholder="Frag Nerio etwas..."
                  className="w-full bg-white/5 border border-white/10 rounded-2xl px-5 py-3 pr-12 focus:outline-none focus:ring-2 focus:ring-white/20 transition-all placeholder:text-white/20"
                />
                <button 
                  onClick={() => !isHoldingRef.current && toggleListening()}
                  onMouseDown={handleMicMouseDown}
                  onMouseUp={handleMicMouseUp}
                  onMouseLeave={handleMicMouseUp}
                  onTouchStart={handleMicMouseDown}
                  onTouchEnd={handleMicMouseUp}
                  className={`absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-xl flex items-center justify-center transition-all ${
                    isListening 
                      ? 'bg-yellow-500 text-black animate-pulse-ring glow-gold scale-110' 
                      : sttEnabled 
                        ? 'text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20' 
                        : 'text-white/30 hover:text-white hover:bg-white/10'
                  }`}
                >
                  <Mic className={`w-4 h-4 ${isListening ? 'animate-bounce' : ''}`} />
                  {sttEnabled && !isListening && (
                    <div className="absolute -top-1 -right-1 w-2 h-2 bg-emerald-500 rounded-full border border-black animate-pulse" />
                  )}
                </button>
              </div>
              <button 
                onClick={() => handleSendMessage()}
                disabled={!input.trim()}
                className={`w-12 h-12 ${getAccentClass('bg')} hover:opacity-90 disabled:bg-white/5 disabled:text-white/20 text-white rounded-2xl flex items-center justify-center transition-all shadow-lg ${getAccentClass('shadow')}`}
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        {/* Integrated Sidebar Settings */}
        <AnimatePresence>
          {showSettings && (
            <>
              {/* Backdrop for clicking outside */}
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => setShowSettings(false)}
                className="absolute inset-0 bg-black/40 z-10"
              />
              <motion.div 
                initial={{ x: '100%' }}
                animate={{ x: 0 }}
                exit={{ x: '100%' }}
                transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                className="absolute right-0 top-0 bottom-0 w-80 bg-[#121212] border-l border-white/10 z-20 flex flex-col"
              >
              <div className="p-6 border-b border-white/10 flex items-center justify-between">
                <h2 className="text-lg font-bold flex items-center gap-2">
                  <Settings className="w-5 h-5 text-white/50" />
                  Einstellungen
                </h2>
                <button 
                  onClick={() => setShowSettings(false)}
                  className="w-8 h-8 rounded-full hover:bg-white/10 flex items-center justify-center transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-6 space-y-8">
                {/* Language / Region */}
                <section className="space-y-4">
                  <h3 className="text-xs font-bold uppercase tracking-widest text-white/30 flex items-center gap-2">
                    <Globe className="w-3 h-3" />
                    Sprache & Region
                  </h3>
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { code: 'de', label: 'Deutsch' },
                      { code: 'en', label: 'English' },
                      { code: 'fr', label: 'Français' },
                      { code: 'es', label: 'Español' },
                    ].map((l) => (
                      <button
                        key={l.code}
                        onClick={() => handleLanguageChange(l.code)}
                        className={`p-3 rounded-xl text-sm font-medium transition-all text-center border ${language === l.code ? `${getAccentClass('bg')}/20 ${getAccentClass('border')} ${getAccentClass('text')}` : 'bg-white/5 border-transparent text-white/50 hover:bg-white/10'}`}
                      >
                        {l.label}
                      </button>
                    ))}
                  </div>
                </section>

                {/* Voice Controls */}
                <section className="space-y-4">
                  <h3 className="text-xs font-bold uppercase tracking-widest text-white/30 flex items-center gap-2">
                    <Zap className="w-3 h-3" />
                    Audio & Voice
                  </h3>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 rounded-2xl bg-white/5 border border-white/10">
                      <div className="flex items-center gap-3">
                        <Volume2 className={`w-4 h-4 ${ttsEnabled ? getAccentClass('text') : 'text-white/30'}`} />
                        <span className="text-sm font-medium">Text-to-Speech</span>
                      </div>
                      <button 
                        onClick={() => setTtsEnabled(!ttsEnabled)}
                        className={`w-10 h-5 rounded-full transition-all relative ${ttsEnabled ? getAccentClass('bg') : 'bg-white/10'}`}
                      >
                        <div className={`absolute top-1 w-3 h-3 rounded-full bg-white transition-all ${ttsEnabled ? 'left-6' : 'left-1'}`} />
                      </button>
                    </div>
                    
                    {ttsEnabled && (
                      <div className="p-2 rounded-xl bg-white/5 border border-white/5 flex gap-1">
                        <button 
                          onClick={() => setTtsMode('server')}
                          className={`flex-1 py-1.5 rounded-lg text-[10px] font-bold transition-all ${ttsMode === 'server' ? getAccentClass('bg') + ' text-white' : 'text-white/30 hover:bg-white/5'}`}
                        >
                          SERVER (HQ)
                        </button>
                        <button 
                          onClick={() => setTtsMode('browser')}
                          className={`flex-1 py-1.5 rounded-lg text-[10px] font-bold transition-all ${ttsMode === 'browser' ? getAccentClass('bg') + ' text-white' : 'text-white/30 hover:bg-white/5'}`}
                        >
                          BROWSER
                        </button>
                      </div>
                    )}

                    <div className="flex items-center justify-between p-3 rounded-2xl bg-white/5 border border-white/10">
                      <div className="flex items-center gap-3">
                        <Mic2 className={`w-4 h-4 ${sttEnabled ? getAccentClass('text') : 'text-white/30'}`} />
                        <span className="text-sm font-medium">Spracherkennung</span>
                      </div>
                      <button 
                        onClick={() => setSttEnabled(!sttEnabled)}
                        className={`w-10 h-5 rounded-full transition-all relative ${sttEnabled ? getAccentClass('bg') : 'bg-white/10'}`}
                      >
                        <div className={`absolute top-1 w-3 h-3 rounded-full bg-white transition-all ${sttEnabled ? 'left-6' : 'left-1'}`} />
                      </button>
                    </div>
                  </div>
                </section>

                {/* Visual Customization */}
                <section className="space-y-4">
                  <h3 className="text-xs font-bold uppercase tracking-widest text-white/30 flex items-center gap-2">
                    <Palette className="w-3 h-3" />
                    Erscheinungsbild
                  </h3>
                  <div className="space-y-4">
                    <div className="p-3 rounded-2xl bg-white/5 border border-white/10 space-y-3">
                      <span className="text-xs font-medium text-white/50 block">Akzentfarbe</span>
                      <div className="flex gap-2">
                        {(Object.keys(accentColors) as AccentColor[]).map((color) => (
                          <button
                            key={color}
                            onClick={() => setAccentColor(color)}
                            className={`w-8 h-8 rounded-full transition-all border-2 ${accentColor === color ? 'border-white scale-110' : 'border-transparent opacity-50 hover:opacity-100'} ${accentColors[color].split(' ')[0]}`}
                          />
                        ))}
                      </div>
                    </div>
                    <div className="flex items-center justify-between p-3 rounded-2xl bg-white/5 border border-white/10">
                      <span className="text-sm font-medium">Kompakter Modus</span>
                      <button 
                        onClick={() => setIsCompact(!isCompact)}
                        className={`w-10 h-5 rounded-full transition-all relative ${isCompact ? getAccentClass('bg') : 'bg-white/10'}`}
                      >
                        <div className={`absolute top-1 w-3 h-3 rounded-full bg-white transition-all ${isCompact ? 'left-6' : 'left-1'}`} />
                      </button>
                    </div>
                  </div>
                </section>

                {/* AI Personality */}
                <section className="space-y-4">
                  <h3 className="text-xs font-bold uppercase tracking-widest text-white/30 flex items-center gap-2">
                    <MessageSquare className="w-3 h-3" />
                    KI-Persönlichkeit
                  </h3>
                  <div className="grid grid-cols-1 gap-2">
                    {(['Professional', 'Friendly', 'Creative'] as Personality[]).map((p) => (
                      <button
                        key={p}
                        onClick={() => setPersonality(p)}
                        className={`p-3 rounded-xl text-sm font-medium transition-all text-left border ${personality === p ? `${getAccentClass('bg')}/20 ${getAccentClass('border')} ${getAccentClass('text')}` : 'bg-white/5 border-transparent text-white/50 hover:bg-white/10'}`}
                      >
                        {p === 'Professional' && '💼 '}
                        {p === 'Friendly' && '😊 '}
                        {p === 'Creative' && '🎨 '}
                        {p}
                      </button>
                    ))}
                  </div>
                </section>
              </div>

              <div className="p-6 border-t border-white/10 bg-white/5">
                <p className="text-[10px] text-center text-white/20 font-mono">
                  NERIO v2.4.0 • STABLE BUILD
                </p>
              </div>
            </motion.div>
            </>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
