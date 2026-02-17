import { EMOJI_CATEGORIES, EMOJI_KEYWORDS } from "./emoji-data.js";

(function () {
  "use strict";

  const textarea = document.getElementById("compose-text");
  const countersEl = document.getElementById("counters");
  const postBtn = document.getElementById("post-btn");
  const statusEl = document.getElementById("status");
  const imageInput = document.getElementById("image-input");
  const imageNameEl = document.getElementById("image-name");
  const clearImageBtn = document.getElementById("clear-image");
  const imageDropzone = document.getElementById("image-dropzone");
  const imageDropzoneHint = document.getElementById("image-dropzone-hint");
  const imageThumbnailWrap = document.getElementById("image-thumbnail-wrap");
  const imageThumbnail = document.getElementById("image-thumbnail");
  const emojiBtn = document.getElementById("emoji-btn");
  const emojiPicker = document.getElementById("emoji-picker");
  const previewContent = document.getElementById("preview-content");
  const tabsContainer = document.getElementById("tabs");
  const draftStateEl = document.getElementById("draft-state");
  const typingMetricsEl = document.getElementById("typing-metrics");
  const enhanceBtn = document.getElementById("enhance-btn");
  const undoEnhanceBtn = document.getElementById("undo-enhance-btn");
  const enhanceStateEl = document.getElementById("enhance-state");

  let activeTab = "twitter";
  let previewData = {};
  let debounceTimer = null;
  let selectedFile = null;
  let imagePreviewUrl = null;
  let saveDraftTimer = null;
  let previousTextBeforeEnhance = "";
  let isEnhancing = false;
  let userProfile = {
    displayName: "Your Name",
    twitterHandle: "@you",
    blueskyHandle: "@you.bsky.social",
    linkedinHeadline: "Your headline",
  };

  const PLATFORM_LABELS = {
    twitter: "Twitter",
    bluesky: "BlueSky",
    linkedin: "LinkedIn",
  };
  const DRAFT_KEY = "cross-poster-draft-v1";

  // --- SVG Icons ---
  const ICONS = {
    reply: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M1.751 10c0-4.42 3.584-8 8.005-8h4.366c4.49 0 8.129 3.64 8.129 8.13 0 2.25-.893 4.29-2.359 5.79l-5.39 5.4c-.3.3-.71.46-1.12.46-.41 0-.82-.16-1.12-.46-.62-.63-.62-1.63 0-2.25l5.37-5.39c.97-.97 1.52-2.28 1.52-3.55 0-2.76-2.24-5.01-5.01-5.01H9.756c-2.76 0-5.01 2.24-5.01 5v.09c0 .87-.71 1.58-1.58 1.58s-1.42-.71-1.42-1.58V10z"/></svg>',
    retweet: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M4.5 3.88l4.432 4.14-1.364 1.46L5.5 7.55V16c0 1.1.896 2 2 2H13v2H7.5c-2.209 0-4-1.79-4-4V7.55L1.432 9.48.068 8.02 4.5 3.88zM16.5 6H11V4h5.5c2.209 0 4 1.79 4 4v8.45l2.068-1.93 1.364 1.46-4.432 4.14-4.432-4.14 1.364-1.46 2.068 1.93V8c0-1.1-.896-2-2-2z"/></svg>',
    heart: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M16.697 5.5c-1.222-.06-2.679.51-3.89 2.16l-.805 1.09-.806-1.09C9.984 6.01 8.526 5.44 7.304 5.5c-1.243.07-2.349.78-2.91 1.91-.552 1.12-.633 2.78.479 4.82 1.074 1.97 3.257 4.27 7.129 6.61 3.87-2.34 6.052-4.64 7.126-6.61 1.111-2.04 1.03-3.7.477-4.82-.56-1.13-1.666-1.84-2.908-1.91z"/></svg>',
    share: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M12 2.59l5.7 5.7-1.41 1.42L13 6.41V16h-2V6.41l-3.3 3.3-1.41-1.42L12 2.59zM21 15l-.02 3.51c0 1.38-1.12 2.49-2.5 2.49H5.5C4.11 21 3 19.88 3 18.5V15h2v3.5c0 .28.22.5.5.5h12.98c.28 0 .5-.22.5-.5L19 15h2z"/></svg>',
    repost: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M4.5 3.88l4.432 4.14-1.364 1.46L5.5 7.55V16c0 1.1.896 2 2 2H13v2H7.5c-2.209 0-4-1.79-4-4V7.55L1.432 9.48.068 8.02 4.5 3.88zM16.5 6H11V4h5.5c2.209 0 4 1.79 4 4v8.45l2.068-1.93 1.364 1.46-4.432 4.14-4.432-4.14 1.364-1.46 2.068 1.93V8c0-1.1-.896-2-2-2z"/></svg>',
    like: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M16.697 5.5c-1.222-.06-2.679.51-3.89 2.16l-.805 1.09-.806-1.09C9.984 6.01 8.526 5.44 7.304 5.5c-1.243.07-2.349.78-2.91 1.91-.552 1.12-.633 2.78.479 4.82 1.074 1.97 3.257 4.27 7.129 6.61 3.87-2.34 6.052-4.64 7.126-6.61 1.111-2.04 1.03-3.7.477-4.82-.56-1.13-1.666-1.84-2.908-1.91z"/></svg>',
    comment: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M1.751 10c0-4.42 3.584-8 8.005-8h4.366c4.49 0 8.129 3.64 8.129 8.13 0 2.25-.893 4.29-2.359 5.79l-5.39 5.4c-.3.3-.71.46-1.12.46-.41 0-.82-.16-1.12-.46-.62-.63-.62-1.63 0-2.25l5.37-5.39c.97-.97 1.52-2.28 1.52-3.55 0-2.76-2.24-5.01-5.01-5.01H9.756c-2.76 0-5.01 2.24-5.01 5v.09c0 .87-.71 1.58-1.58 1.58s-1.42-.71-1.42-1.58V10z"/></svg>',
    send: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M21 3L0 10l7.66 4.26L14 8l-6.26 8.34L12 24l9-21z"/></svg>',
    more: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M3 12c0-1.1.9-2 2-2s2 .9 2 2-.9 2-2 2-2-.9-2-2zm9 2c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm7 0c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2z"/></svg>',
    thumbsup: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M13.11 5.72l-.57 2.89c-.12.59.04 1.2.42 1.66.38.46.94.73 1.54.73H20v1.08L17.43 18H9.34c-.18 0-.34-.16-.34-.34V9.82l4.11-4.1M14 2L7.59 8.41C7.21 8.79 7 9.3 7 9.83v7.83C7 18.95 8.05 20 9.34 20h8.1c.71 0 1.36-.37 1.72-.97l2.67-6.15c.11-.25.17-.52.17-.8V11c0-1.1-.9-2-2-2h-5.5l.92-4.65c.05-.22.02-.46-.08-.66-.23-.45-.52-.86-.88-1.22L14 2zM4 9H2v11h2c.55 0 1-.45 1-1v-9c0-.55-.45-1-1-1z"/></svg>',
  };

  // --- Platform checkboxes ---
  function getEnabledPlatforms() {
    return Array.from(
      document.querySelectorAll('input[name="platform"]:checked')
    ).map((cb) => cb.value);
  }

  document.querySelectorAll('input[name="platform"]').forEach((cb) => {
    cb.addEventListener("change", () => {
      updateTabs();
      updatePostBtn();
      requestPreview();
    });
  });

  // --- Tabs ---
  function updateTabs() {
    const enabled = getEnabledPlatforms();
    tabsContainer.querySelectorAll(".tab").forEach((tab) => {
      const p = tab.dataset.platform;
      if (enabled.includes(p)) {
        tab.classList.remove("disabled");
      } else {
        tab.classList.add("disabled");
        if (activeTab === p) {
          // switch to first enabled tab
          const first = enabled[0];
          if (first) setActiveTab(first);
        }
      }
    });
  }

  function setActiveTab(platform) {
    activeTab = platform;
    tabsContainer.querySelectorAll(".tab").forEach((tab) => {
      tab.classList.toggle("active", tab.dataset.platform === platform);
    });
    renderPreview();
  }

  tabsContainer.addEventListener("click", (e) => {
    const tab = e.target.closest(".tab");
    if (!tab || tab.classList.contains("disabled")) return;
    setActiveTab(tab.dataset.platform);
  });

  // --- Compose & Preview ---
  textarea.addEventListener("input", () => {
    updateTypingMetrics();
    queueDraftSave();
    updatePostBtn();
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(requestPreview, 300);
  });

  function updateTypingMetrics() {
    const text = textarea.value.trim();
    const chars = textarea.value.length;
    const words = text ? text.split(/\s+/).length : 0;
    typingMetricsEl.textContent = `${chars} chars · ${words} words`;
  }

  function queueDraftSave() {
    clearTimeout(saveDraftTimer);
    draftStateEl.textContent = "Saving draft...";
    saveDraftTimer = setTimeout(() => {
      localStorage.setItem(DRAFT_KEY, textarea.value);
      const timestamp = new Date().toLocaleTimeString([], {
        hour: "numeric",
        minute: "2-digit",
      });
      draftStateEl.textContent = `Draft saved at ${timestamp}`;
    }, 250);
  }

  // --- Emoji Picker ---
  function normalizeForSearch(text) {
    return (text || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }

  function buildEmojiSections(query) {
    const q = normalizeForSearch(query).trim();
    const sections = [];

    for (const category of EMOJI_CATEGORIES) {
      const items = q
        ? category.emojis.filter((emoji) => {
            const haystack = normalizeForSearch(
              `${category.name} ${EMOJI_KEYWORDS[emoji] || ""} ${emoji}`
            );
            return haystack.includes(q);
          })
        : category.emojis;

      if (items.length > 0) {
        sections.push({ name: category.name, emojis: items });
      }
    }

    return sections;
  }

  function renderEmojiSections(query) {
    const sections = buildEmojiSections(query);

    if (sections.length === 0) {
      return '<p class="emoji-no-results">No emojis matched that search.</p>';
    }

    return sections
      .map((category) => {
        const buttons = category.emojis
          .map(
            (emoji) =>
              `<button class="emoji-option" type="button" data-emoji="${emoji}" aria-label="Insert ${emoji}">${emoji}</button>`
          )
          .join("");
        return `<section class="emoji-section">
          <h4 class="emoji-section-title">${escapeHtml(category.name)}</h4>
          <div class="emoji-grid">${buttons}</div>
        </section>`;
      })
      .join("");
  }

  function renderEmojiPicker() {
    emojiPicker.innerHTML = `
      <div class="emoji-picker-header">
        <span class="emoji-picker-title">Choose an emoji</span>
        <button class="emoji-picker-close" type="button" aria-label="Close emoji picker">✕</button>
      </div>
      <input id="emoji-search-input" class="emoji-search-input" type="text" placeholder="Search emoji (e.g. tea, fire, launch)">
      <div class="emoji-picker-body" id="emoji-picker-body">${renderEmojiSections("")}</div>
    `;

    const searchInput = emojiPicker.querySelector("#emoji-search-input");
    const body = emojiPicker.querySelector("#emoji-picker-body");
    searchInput.addEventListener("input", () => {
      body.innerHTML = renderEmojiSections(searchInput.value);
    });
  }

  function closeEmojiPicker() {
    emojiPicker.hidden = true;
    emojiBtn.classList.remove("active");
  }

  function insertAtCursor(text) {
    const start = textarea.selectionStart || 0;
    const end = textarea.selectionEnd || 0;
    const current = textarea.value;
    textarea.value = current.slice(0, start) + text + current.slice(end);
    const nextPos = start + text.length;
    textarea.selectionStart = nextPos;
    textarea.selectionEnd = nextPos;
    textarea.focus();
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
  }

  renderEmojiPicker();

  emojiBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    if (emojiPicker.hidden) {
      emojiPicker.hidden = false;
      emojiBtn.classList.add("active");
      const searchInput = emojiPicker.querySelector("#emoji-search-input");
      const body = emojiPicker.querySelector("#emoji-picker-body");
      if (searchInput && body) {
        searchInput.value = "";
        body.innerHTML = renderEmojiSections("");
        searchInput.focus();
      }
      return;
    }
    closeEmojiPicker();
  });

  emojiPicker.addEventListener("click", (e) => {
    if (e.target.closest(".emoji-picker-close")) {
      closeEmojiPicker();
      return;
    }
    const option = e.target.closest(".emoji-option");
    if (!option) return;
    insertAtCursor(option.dataset.emoji);
    closeEmojiPicker();
  });

  document.addEventListener("click", (e) => {
    if (
      !emojiPicker.hidden &&
      !emojiPicker.contains(e.target) &&
      !emojiBtn.contains(e.target)
    ) {
      closeEmojiPicker();
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !emojiPicker.hidden) {
      closeEmojiPicker();
    }
  });

  function updatePostBtn() {
    const hasText = textarea.value.trim().length > 0;
    const hasPlatforms = getEnabledPlatforms().length > 0;
    postBtn.disabled = !(hasText && hasPlatforms);
  }

  function setEnhanceState(message, isError) {
    enhanceStateEl.textContent = message || "";
    enhanceStateEl.classList.toggle("error", Boolean(isError));
  }

  function enhanceText() {
    const original = textarea.value.trim();
    if (!original || isEnhancing) return;

    isEnhancing = true;
    enhanceBtn.disabled = true;
    enhanceBtn.textContent = "Enhancing...";
    setEnhanceState("Polishing tone for social media...", false);

    fetch("/api/enhance", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: original }),
    })
      .then((r) =>
        r.json().then((data) => ({
          ok: r.ok,
          data,
        }))
      )
      .then(({ ok, data }) => {
        if (!ok) {
          throw new Error(data.error || "Enhancement failed");
        }
        const enhanced = (data.text || "").trim();
        if (!enhanced) {
          throw new Error("Enhancement returned empty text");
        }

        previousTextBeforeEnhance = textarea.value;
        textarea.value = enhanced;
        textarea.dispatchEvent(new Event("input", { bubbles: true }));
        undoEnhanceBtn.hidden = false;
        setEnhanceState("Enhanced with a casual-professional voice.", false);
      })
      .catch((err) => {
        setEnhanceState(err.message, true);
      })
      .finally(() => {
        isEnhancing = false;
        enhanceBtn.disabled = false;
        enhanceBtn.textContent = "AI Enhance";
      });
  }

  enhanceBtn.addEventListener("click", enhanceText);

  undoEnhanceBtn.addEventListener("click", () => {
    if (!previousTextBeforeEnhance) return;
    textarea.value = previousTextBeforeEnhance;
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    previousTextBeforeEnhance = "";
    undoEnhanceBtn.hidden = true;
    setEnhanceState("Reverted to your previous draft.", false);
  });

  function requestPreview() {
    const text = textarea.value;
    const platforms = getEnabledPlatforms();

    if (!text.trim() || platforms.length === 0) {
      previewData = {};
      countersEl.innerHTML = "";
      renderPreview();
      return;
    }

    previewContent.classList.add("is-refreshing");
    fetch("/api/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, platforms }),
    })
      .then((r) => r.json())
      .then((data) => {
        previewData = data;
        updateCounters();
        renderPreview();
      })
      .catch(() => {})
      .finally(() => {
        previewContent.classList.remove("is-refreshing");
      });
  }

  function updateCounters() {
    const enabled = getEnabledPlatforms();
    const parts = [];
    for (const key of enabled) {
      const d = previewData[key];
      if (!d || d.limit === null) continue;
      const cls = d.over ? "counter-card over" : "counter-card";
      const pct = Math.min(100, Math.round((d.count / d.limit) * 100));
      parts.push(
        `<div class="${cls}">
          <div class="counter-top">
            <span>${PLATFORM_LABELS[key]}</span>
            <strong>${d.count}/${d.limit}</strong>
          </div>
          <div class="counter-track"><span style="width:${pct}%"></span></div>
        </div>`
      );
    }
    countersEl.innerHTML = parts.join("");
  }

  function renderPreview() {
    const d = previewData[activeTab];
    if (!d) {
      previewContent.innerHTML =
        '<p class="empty-state">Start typing to see a preview...</p>';
      return;
    }

    const parts = d.parts;
    let html = "";

    if (d.limit !== null) {
      html += `<div class="preview-info">${d.count}/${d.limit} chars &middot; ${parts.length} post${parts.length > 1 ? "s" : ""}</div>`;
    } else {
      html += `<div class="preview-info">${d.count} chars &middot; No limit</div>`;
    }

    if (activeTab === "twitter") {
      html += renderTwitterCards(parts);
    } else if (activeTab === "bluesky") {
      html += renderBlueskyCards(parts);
    } else if (activeTab === "linkedin") {
      html += renderLinkedInCards(parts);
    }

    previewContent.innerHTML = html;
  }

  function renderTwitterCards(parts) {
    let html = '<div class="twitter-thread">';
    for (let i = 0; i < parts.length; i++) {
      const showConnector = i < parts.length - 1;
      html += `<div class="twitter-card">
        <div class="twitter-avatar-col">
          <div class="twitter-avatar"></div>
          ${showConnector ? '<div class="twitter-connector"></div>' : ""}
        </div>
        <div class="twitter-content">
          <div class="twitter-header">
            <span class="twitter-name">${escapeHtml(userProfile.displayName)}</span>
            <span class="twitter-handle">&middot; ${escapeHtml(userProfile.twitterHandle)} &middot; now</span>
          </div>
          <div class="twitter-body">${escapeHtml(parts[i])}</div>
          ${i === 0 && imagePreviewUrl ? `<img class="twitter-image" src="${imagePreviewUrl}">` : ""}
          <div class="twitter-actions">
            <span class="twitter-action">${ICONS.reply}</span>
            <span class="twitter-action">${ICONS.retweet}</span>
            <span class="twitter-action">${ICONS.heart}</span>
            <span class="twitter-action">${ICONS.share}</span>
          </div>
        </div>
      </div>`;
    }
    html += "</div>";
    return html;
  }

  function renderBlueskyCards(parts) {
    let html = '<div class="bluesky-thread">';
    for (let i = 0; i < parts.length; i++) {
      const showConnector = i < parts.length - 1;
      html += `<div class="bluesky-card">
        <div class="bluesky-avatar-col">
          <div class="bluesky-avatar"></div>
          ${showConnector ? '<div class="bluesky-connector"></div>' : ""}
        </div>
        <div class="bluesky-content">
          <div class="bluesky-header">
            <span class="bluesky-name">${escapeHtml(userProfile.displayName)}</span>
            <span class="bluesky-handle">${escapeHtml(userProfile.blueskyHandle)} &middot; now</span>
          </div>
          <div class="bluesky-body">${escapeHtml(parts[i])}</div>
          ${i === 0 && imagePreviewUrl ? `<img class="bluesky-image" src="${imagePreviewUrl}">` : ""}
          <div class="bluesky-actions">
            <span class="bluesky-action">${ICONS.comment}</span>
            <span class="bluesky-action">${ICONS.repost}</span>
            <span class="bluesky-action">${ICONS.like}</span>
            <span class="bluesky-action">${ICONS.more}</span>
          </div>
        </div>
      </div>`;
    }
    html += "</div>";
    return html;
  }

  function renderLinkedInCards(parts) {
    let html = '<div class="linkedin-thread">';
    for (let i = 0; i < parts.length; i++) {
      html += `<div class="linkedin-card">
        <div class="linkedin-header">
          <div class="linkedin-avatar"></div>
          <div class="linkedin-header-text">
            <div class="linkedin-name">${escapeHtml(userProfile.displayName)}</div>
            <div class="linkedin-subtitle">${escapeHtml(userProfile.linkedinHeadline)} &middot; now</div>
          </div>
        </div>
        <div class="linkedin-body">${escapeHtml(parts[i])}</div>
        ${i === 0 && imagePreviewUrl ? `<img class="linkedin-image" src="${imagePreviewUrl}">` : ""}
        <div class="linkedin-engagement">
          ${ICONS.thumbsup} <span>0</span>
        </div>
        <div class="linkedin-actions-row">
          <span class="linkedin-action-btn">${ICONS.thumbsup} Like</span>
          <span class="linkedin-action-btn">${ICONS.comment} Comment</span>
          <span class="linkedin-action-btn">${ICONS.repost} Repost</span>
          <span class="linkedin-action-btn">${ICONS.send} Send</span>
        </div>
      </div>`;
    }
    html += "</div>";
    return html;
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  // --- Image Attachment ---
  function clearSelectedImage() {
    selectedFile = null;
    if (imagePreviewUrl) {
      URL.revokeObjectURL(imagePreviewUrl);
      imagePreviewUrl = null;
    }
    imageInput.value = "";
    imageThumbnail.removeAttribute("src");
    imageNameEl.textContent = "";
    imageThumbnailWrap.hidden = true;
    imageDropzone.classList.remove("has-file");
    imageDropzone.classList.remove("drag-over");
    imageDropzoneHint.textContent = "or click to browse PNG, JPG, or GIF";
    renderPreview();
  }

  function clearComposerAfterSuccessfulPost() {
    textarea.value = "";
    localStorage.removeItem(DRAFT_KEY);
    draftStateEl.textContent = "Draft cleared after publishing";
    previousTextBeforeEnhance = "";
    undoEnhanceBtn.hidden = true;
    setEnhanceState("", false);
    clearSelectedImage();
    previewData = {};
    countersEl.innerHTML = "";
    updateTypingMetrics();
    updatePostBtn();
    renderPreview();
  }

  function setSelectedImage(file) {
    if (!file || !file.type || !file.type.startsWith("image/")) {
      statusEl.innerHTML = '<div class="platform-result error">Please choose a valid image file.</div>';
      return;
    }

    selectedFile = file;
    if (imagePreviewUrl) URL.revokeObjectURL(imagePreviewUrl);
    imagePreviewUrl = URL.createObjectURL(file);
    imageNameEl.textContent = file.name;
    imageThumbnail.src = imagePreviewUrl;
    imageThumbnailWrap.hidden = false;
    imageDropzone.classList.add("has-file");
    imageDropzoneHint.textContent = "Drop a new image to replace this one";
    renderPreview();
  }

  imageInput.addEventListener("change", () => {
    const file = imageInput.files[0];
    if (file) setSelectedImage(file);
  });

  imageDropzone.addEventListener("click", () => {
    imageInput.click();
  });

  imageDropzone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      imageInput.click();
    }
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    imageDropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      imageDropzone.classList.add("drag-over");
    });
  });

  ["dragleave", "dragend"].forEach((eventName) => {
    imageDropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      imageDropzone.classList.remove("drag-over");
    });
  });

  imageDropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    e.stopPropagation();
    imageDropzone.classList.remove("drag-over");
    const file = e.dataTransfer && e.dataTransfer.files ? e.dataTransfer.files[0] : null;
    if (file) setSelectedImage(file);
  });

  clearImageBtn.addEventListener("click", clearSelectedImage);

  // --- Posting ---
  function postNow() {
    const text = textarea.value.trim();
    const platforms = getEnabledPlatforms();
    if (!text || platforms.length === 0) return;

    postBtn.disabled = true;
    statusEl.innerHTML = '<div class="posting">Publishing across selected platforms...</div>';

    const formData = new FormData();
    formData.append("text", text);
    platforms.forEach((p) => formData.append("platforms", p));
    if (selectedFile) {
      formData.append("image", selectedFile);
    }

    fetch("/api/post", {
      method: "POST",
      body: formData,
    })
      .then((r) => r.json())
      .then((results) => {
        let html = "";
        let allSuccess = true;
        for (const [key, result] of Object.entries(results)) {
          const label = PLATFORM_LABELS[key] || key;
          if (result.success) {
            const link = Array.isArray(result.urls) && result.urls.length > 0
              ? ` <a class="result-link" href="${escapeHtml(result.urls[0])}" target="_blank" rel="noopener noreferrer">View</a><button class="copy-link-btn" type="button" data-url="${encodeURIComponent(result.urls[0])}">Copy link</button>`
              : "";
            html += `<div class="platform-result success">${label}: Published${link}</div>`;
          } else {
            allSuccess = false;
            html += `<div class="platform-result error">${label}: ${escapeHtml(result.error || "Unknown error")}</div>`;
          }
        }
        statusEl.innerHTML = html;
        if (allSuccess) {
          clearComposerAfterSuccessfulPost();
        } else {
          updatePostBtn();
        }
      })
      .catch((err) => {
        statusEl.innerHTML = `<div class="platform-result error">Request failed: ${escapeHtml(err.message)}</div>`;
        updatePostBtn();
      });
  }

  postBtn.addEventListener("click", postNow);

  statusEl.addEventListener("click", (e) => {
    const btn = e.target.closest(".copy-link-btn");
    if (!btn) return;

    const encodedUrl = btn.dataset.url || "";
    const url = decodeURIComponent(encodedUrl);
    if (!url) return;

    const setCopiedState = () => {
      const prev = btn.textContent;
      btn.textContent = "Copied";
      btn.disabled = true;
      setTimeout(() => {
        btn.textContent = prev;
        btn.disabled = false;
      }, 1000);
    };

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(setCopiedState).catch(() => {});
      return;
    }

    const temp = document.createElement("textarea");
    temp.value = url;
    document.body.appendChild(temp);
    temp.select();
    try {
      document.execCommand("copy");
      setCopiedState();
    } catch (_) {}
    document.body.removeChild(temp);
  });

  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      postNow();
    }
  });

  // --- LinkedIn OAuth ---
  if (window.__linkedinStatus) {
    const cls =
      window.__linkedinStatus === "success" ? "success" : "error";
    statusEl.innerHTML = `<div class="platform-result ${cls}">${escapeHtml(window.__linkedinMessage)}</div>`;
  }

  // Initialize
  const savedDraft = localStorage.getItem(DRAFT_KEY);
  if (savedDraft) {
    textarea.value = savedDraft;
    draftStateEl.textContent = "Draft restored";
  }
  updateTypingMetrics();
  updateTabs();
  updatePostBtn();
  requestPreview();

  fetch("/api/profile")
    .then((r) => r.json())
    .then((data) => {
      userProfile = data;
    })
    .catch(() => {});
})();
