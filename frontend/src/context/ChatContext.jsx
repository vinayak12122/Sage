
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { useMatch, useNavigate } from "react-router-dom";
import { useAuth } from "./AuthContext";

const API = import.meta.env.VITE_BACKEND_URL;
const ChatContext = createContext(null);

export const ChatProvider = ({ children }) => {
    const navigate = useNavigate();
    const { isAuthenticated } = useAuth();
    const sessionId = useMatch('/chat/:sessionId')?.params.sessionId;

    const [messages, setMessages] = useState([]);
    const [sessions, setSessions] = useState([]);
    const [isStreaming, setIsStreaming] = useState(false);

    const abortRef = useRef(null);
    const readerRef = useRef(null);
    const freshRef = useRef(null);
    const requestRef = useRef(0);

    useEffect(() => {
        if (!isAuthenticated) {
            setSessions([]);
            return;
        }

        fetch(`${API}/chat`, { credentials: 'include' })
            .then(r => r.ok ? r.json() : [])
            .then(setSessions)
            .catch(() => { });
    }, [isAuthenticated]);

    useEffect(() => {
        if (sessionId && freshRef.current === sessionId) return;

        freshRef.current = null;

        requestRef.current++;
        abortRef.current?.abort();
        readerRef.current?.cancel().catch(() => { });

        abortRef.current = null;
        readerRef.current = null;
        setIsStreaming(false);

        if (!sessionId) {
            setMessages([]);
            return;
        }

        const ctrl = new AbortController();

        fetch(`${API}/chat/${sessionId}`, {
            credentials: 'include',
            signal: ctrl.signal
        })
            .then(r => r.ok ? r.json() : Promise.reject(r.status))
            .then(data => {
                if (!ctrl.signal.aborted) {
                    setMessages(data.map(({ role, content }) => ({
                        role,
                        content
                    })));
                }
            })
            .catch(() => {
                if (!ctrl.signal.aborted) setMessages([]);
            });

        return () => ctrl.abort();
    }, [sessionId]);

    const patchLast = useCallback((fn, requestId) => {
        if (requestRef.current !== requestId) return;

        setMessages(m =>
            m.length
                ? [...m.slice(0, -1), fn(m[m.length - 1])]
                : m
        );
    }, []);

    // Stop active generation
    const stopGeneration = useCallback(() => {
        const ctrl = abortRef.current;

        if (!ctrl) return;

        // Invalidate the current request first.
        requestRef.current++;

        // Abort HTTP request.
        ctrl.abort();

        // Cancel response reader.
        readerRef.current?.cancel().catch(() => { });

        abortRef.current = null;
        readerRef.current = null;

        // Preserve partial response and mark it stopped.
        setMessages(m => {
            if (!m.length) return m;

            const last = m[m.length - 1];

            if (last.role !== 'assistant') return m;

            return [
                ...m.slice(0, -1),
                { ...last, stopped: true }
            ];
        });

        setIsStreaming(false);
    }, []);

    const sendMessage = useCallback(async (text) => {
        if (abortRef.current) return;

        let id = sessionId;

        if (!id) {
            id = crypto.randomUUID();
            freshRef.current = id;
            navigate(`/chat/${id}`);

            setSessions(s => [{
                session_id: id,
                created_at: new Date().toISOString(),
                preview: text.slice(0, 60)
            }, ...s]);
        }

        setMessages(m => [
            ...m,
            { role: 'user', content: text },
            { role: 'assistant', content: '' }
        ]);

        const ctrl = new AbortController();
        const requestId = ++requestRef.current;

        abortRef.current = ctrl;
        setIsStreaming(true);

        try {
            const res = await fetch(`${API}/chat/${id}`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text }),
                signal: ctrl.signal
            });

            if (!res.ok || !res.body) {
                throw new Error(`HTTP ${res.status}`);
            }

            const reader = res.body.getReader();
            readerRef.current = reader;

            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();

                if (done || requestRef.current !== requestId) break;

                const chunk = decoder.decode(value, { stream: true });

                if (chunk) {
                    patchLast(msg => ({
                        ...msg,
                        content: msg.content + chunk
                    }), requestId);
                }
            }

            if (requestRef.current === requestId) {
                const remaining = decoder.decode();

                if (remaining) {
                    patchLast(msg => ({
                        ...msg,
                        content: msg.content + remaining
                    }), requestId);
                }
            }

        } catch (error) {
            if (
                error.name !== 'AbortError' &&
                requestRef.current === requestId
            ) {
                patchLast(msg => ({
                    ...msg,
                    content: msg.content || 'Something went wrong. Please try again.',
                    error: true
                }), requestId);
            }
        } finally {
            // An older request must not reset a newer request's state.
            if (requestRef.current === requestId) {
                abortRef.current = null;
                readerRef.current = null;
                setIsStreaming(false);
            }
        }
    }, [sessionId, navigate, patchLast]);

    return (
        <ChatContext.Provider value={{
            sessionId,
            messages,
            sessions,
            isStreaming,
            sendMessage,
            stopGeneration
        }}>
            {children}
        </ChatContext.Provider>
    );
};

export const useChat = () => useContext(ChatContext);
