// src/agents/geminiAgent.js
// Connects to Google Gemini API to analyse interview answers

import { GoogleGenerativeAI } from "@google/generative-ai";

// Initialize Gemini with your free API key from https://aistudio.google.com
const genAI = new GoogleGenerativeAI(import.meta.env.VITE_GEMINI_API_KEY);

// Use Gemini 1.5 Flash — fast and free tier supported
const model = genAI.getGenerativeModel({ model: "gemini-2.5-flash" });

/**
 * Analyse the user's interview answer using Gemini
 * @param {string} question - The interview question asked
 * @param {string} answer - The user's spoken answer (transcribed text)
 * @returns {object} - Feedback object with scores and suggestions
 */
export async function analyseAnswer(question, answer) {
  // Build a structured prompt for Gemini to evaluate the answer
  const prompt = `
    You are an expert interview coach. Evaluate the following interview answer.

    Question: "${question}"
    Answer: "${answer}"

    Provide feedback in this exact JSON format (no extra text):
    {
      "relevanceScore": <number 1-10>,
      "clarityScore": <number 1-10>,
      "confidenceScore": <number 1-10>,
      "fillerWords": <number of filler words like um, uh, like>,
      "strengths": "<one sentence about what was good>",
      "improvement": "<one sentence on what to improve>",
      "overallScore": <number 1-10>
    }
  `;

  try {
    // Send prompt to Gemini and wait for response
    const result = await model.generateContent(prompt);
    const text = result.response.text();

    // Extract JSON from Gemini response
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (!jsonMatch) throw new Error("No JSON found in Gemini response");

    // Parse and return the feedback object
    return JSON.parse(jsonMatch[0]);
  } catch (error) {
    console.error("Gemini analysis error:", error);
    // Return default feedback if Gemini fails
    return {
      relevanceScore: 0,
      clarityScore: 0,
      confidenceScore: 0,
      fillerWords: 0,
      strengths: "Could not analyse answer.",
      improvement: "Please try again.",
      overallScore: 0,
    };
  }
}

/**
 * Generate a random interview question using Gemini
 * @param {string} role - Job role e.g. "Software Engineer"
 * @returns {string} - Interview question
 */
export async function generateQuestion(role) {
  const prompt = `Generate one short, realistic interview question for a ${role} position. 
  Return only the question text, nothing else.`;

  try {
    const result = await model.generateContent(prompt);
    return result.response.text().trim();
  } catch (error) {
    console.error("Question generation error:", error);
    // Fallback question if Gemini fails
    return "Tell me about yourself and your experience.";
  }
}
