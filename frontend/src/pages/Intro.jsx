import { useEffect, useRef } from "react";
import anime from "animejs/lib/anime.es.js";
import { useNavigate } from "react-router-dom";

const WORD = "Sage";
const WORDS = ["Small", "Autonomous", "Generative", "Engine"];
const POOL = "abcdefghijklmnopqrstuvwxyzAGSE";

export default function Intro({ onEnter }) {
    const rootRef = useRef(null);
    const wordRef = useRef(null);
    const taglineRef = useRef(null);
    const caretRef = useRef(null);
    const navigate = useNavigate();

    useEffect(() => {
        let done = false;
        let timers = [];
        let fallback;

        const letters = wordRef.current.querySelectorAll(".sg-letter");
        const words = taglineRef.current.querySelectorAll(".sg-word");
        const caret = caretRef.current;
        const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

        const clearTimers = () => {
            timers.forEach((t) => {
                clearInterval(t);
                clearTimeout(t);
            });
            timers = [];
        };

        const finish = () => {
            if (done) return;
            done = true;
            if (onEnter) onEnter();
            navigate("/chat", { replace: true });
        };

        // same scramble effect as before: random glyphs, then settle on the real letter
        const scramble = (node, finalChar, duration) => {
            const start = performance.now();
            const timer = setInterval(() => {
                if (performance.now() - start >= duration) {
                    clearInterval(timer);
                    node.textContent = finalChar;
                    return;
                }
                node.textContent = POOL[Math.floor(Math.random() * POOL.length)];
            }, 55);
            return timer;
        };

        if (reduced) {
            anime.set([...letters, ...words], { opacity: 1, translateY: 0 });
            anime.set(caret, { opacity: 0 });
            fallback = setTimeout(finish, 2500);
            return () => clearTimeout(fallback);
        }

        anime.set(letters, { opacity: 0, translateY: 14 });
        anime.set(words, { opacity: 0, translateY: 8 });
        anime.set(caret, { opacity: 0 });

        const tl = anime.timeline({ easing: "easeOutSine", complete: finish });

        tl.add(
            {
                targets: letters,
                opacity: [0, 1],
                translateY: [14, 0],
                duration: 520,
                delay: anime.stagger(130),
                begin: () => {
                    letters.forEach((node, i) => timers.push(scramble(node, WORD[i], 380 + i * 130)));
                },
            },
            200
        )
            .add({ targets: caret, opacity: [0, 1], duration: 120 }, 1000)
            .add(
                { targets: words, opacity: [0, 1], translateY: [8, 0], duration: 340, delay: anime.stagger(190) },
                1050
            )
            .add({ targets: caret, opacity: [1, 0], duration: 300 }, 2100)
            // hold on the finished state, then fade out (total ≈ 3.9s)
            .add({ targets: rootRef.current, opacity: [1, 0], duration: 450, easing: "easeInQuad" }, 3450);

        // caret blink, same as the original
        timers.push(
            setInterval(() => {
                caret.style.visibility = caret.style.visibility === "hidden" ? "visible" : "hidden";
            }, 480)
        );

        // safety net in case the timeline callback never fires
        fallback = setTimeout(finish, 5000);

        return () => {
            clearTimeout(fallback);
            clearTimers();
            tl.pause();
            anime.remove([...letters, ...words, caret, rootRef.current]);
        };
    }, [navigate, onEnter]);

    return (
        <div ref={rootRef} className="sg-root" aria-label="Sage — Small Autonomous Generative Engine">
            <h1 className="sg-letters" ref={wordRef} aria-hidden="true">
                {WORD.split("").map((l, i) => (
                    <span className="sg-letter" key={i}>
                        {l}
                    </span>
                ))}
            </h1>

            <p className="sg-tagline" ref={taglineRef} aria-hidden="true">
                {WORDS.map((w) => (
                    <span className="sg-word" key={w}>
                        <span className="sg-i">{w[0]}</span>
                        {w.slice(1)}
                    </span>
                ))}
                {/* <span className="sg-caret" ref={caretRef} /> */}
            </p>
        </div>
    );
}