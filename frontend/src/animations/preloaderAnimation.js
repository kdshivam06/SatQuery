import gsap from "gsap";
import { CustomEase } from "gsap/CustomEase";

gsap.registerPlugin(CustomEase);

// Register custom easing functions
try {
    CustomEase.create("hop", "0.9, 0, 0.1, 1");
    CustomEase.create("glide", "0.8, 0, 0.2, 1");
} catch (e) {
    // Easing already registered
}

/**
 * Initializes the preloader intro animation.
 * @param {HTMLElement} scopeElement - Root element containing preloader components.
 * @param {Function} onIntroComplete - Callback executed when intro animation completes and button is ready.
 * @returns {gsap.core.Timeline} The intro timeline.
 */
export const runIntroAnimation = (scopeElement, onIntroComplete) => {
    if (!scopeElement) return null;

    const btnOutlineTrack = scopeElement.querySelector(".stroke-track");
    const btnOutlineProgress = scopeElement.querySelector(".stroke-progress");
    const preloaderBtn = scopeElement.querySelector(".preloader-btn-container");

    if (!btnOutlineTrack || !btnOutlineProgress) return null;

    const svgPathLength = btnOutlineTrack.getTotalLength();

    gsap.set([btnOutlineTrack, btnOutlineProgress], {
        strokeDasharray: svgPathLength,
        strokeDashoffset: svgPathLength,
    });

    const introTl = gsap.timeline({
        delay: 0.5,
    });

    introTl
        .to(scopeElement.querySelectorAll(".preloader .p-row p .line"), {
            y: "0%",
            duration: 0.75,
            ease: "power3.out",
            stagger: 0.1,
        })
        .to(btnOutlineTrack, {
            strokeDashoffset: 0,
            duration: 2,
            ease: "hop",
        })
        .to(
            scopeElement.querySelector(".pbc-svg-strokes svg"),
            {
                rotation: 270,
                duration: 2,
                ease: "hop",
            },
            "<"
        );

    const progressStops = [0.2, 0.45, 0.85, 1].map((base, i) => {
        if (i === 3) return 1;
        return base + (Math.random() - 0.5) * 0.1;
    });

    progressStops.forEach((stop, i) => {
        introTl.to(btnOutlineProgress, {
            strokeDashoffset: svgPathLength - svgPathLength * stop,
            duration: 0.75,
            ease: "glide",
            delay: i === 0 ? 0.2 : 0.2 + Math.random() * 0.15,
        });
    });

    introTl
        .to(
            scopeElement.querySelector("#pbc-logo"),
            {
                opacity: 0,
                duration: 0.35,
                ease: "power1.out",
            },
            "-=0.25"
        )
        .to(
            preloaderBtn,
            {
                scale: 0.9,
                duration: 1.5,
                ease: "hop",
            },
            "-=0.5"
        )
        .to(
            scopeElement.querySelectorAll("#pbc-label .line"),
            {
                y: "0%",
                duration: 0.75,
                ease: "power3.out",
                onComplete: () => {
                    if (onIntroComplete) onIntroComplete();
                },
            },
            "-=0.75"
        );

    return introTl;
};

/**
 * Executes the exit transition when user clicks "Initiate".
 * @param {HTMLElement} scopeElement - Root element containing preloader components.
 * @param {Function} onExitComplete - Optional callback when total exit animation finishes.
 */
export const runExitAnimation = (scopeElement, onExitComplete) => {
    if (!scopeElement) return;

    const btnOutlineTrack = scopeElement.querySelector(".stroke-track");
    const btnOutlineProgress = scopeElement.querySelector(".stroke-progress");

    const svgPathLength = btnOutlineTrack ? btnOutlineTrack.getTotalLength() : 974;

    const exitTl = gsap.timeline();

    exitTl
        .to(scopeElement.querySelector(".preloader"), {
            scale: 0.75,
            duration: 1.25,
            ease: "hop",
        })
        .to(
            [btnOutlineTrack, btnOutlineProgress],
            {
                strokeDashoffset: -svgPathLength,
                duration: 1.25,
                ease: "hop",
            },
            "<"
        )
        .to(
            scopeElement.querySelectorAll("#pbc-label .line"),
            {
                y: "-100%",
                duration: 0.75,
                ease: "power3.out",
            },
            "-=1.25"
        )
        .to(
            scopeElement.querySelectorAll("#pbc-outro-label .line"),
            {
                y: "0%",
                duration: 0.75,
                ease: "power3.out",
            },
            "-=0.75"
        )
        .to(scopeElement.querySelector(".preloader"), {
            clipPath: "polygon(0% 0%, 0% 0%, 0% 100%, 0% 100%)",
            duration: 1.5,
            ease: "hop",
        })
        .to(
            scopeElement.querySelector(".preloader-revealer"),
            {
                clipPath: "polygon(0% 0%, 0% 0%, 0% 100%, 0% 100%)",
                duration: 1.5,
                ease: "hop",
                onComplete: () => {
                    gsap.set(scopeElement.querySelector(".preloader"), {
                        display: "none",
                    });
                    if (onExitComplete) onExitComplete();
                },
            },
            "-=1.45"
        )
        .to(scopeElement.querySelector(".hero"), {
            scale: 1,
            duration: 1.25,
            ease: "hop",
        })
        .to(
            scopeElement.querySelectorAll(".hero-title-word"),
            {
                y: "0%",
                duration: 1,
                ease: "glide",
                stagger: 0.05,
            },
            "-=1.75"
        );

    return exitTl;
};