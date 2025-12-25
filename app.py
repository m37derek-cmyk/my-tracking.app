with tab2:
    t2_1, t2_2, t2_3 = st.tabs(["🥇 العام", "📅 الأسبوعي", "🌟 اليومي"])
    
    with t2_1:
        if not leaderboard.empty:
            st.dataframe(leaderboard[['الترتيب', 'الاسم', 'المستوى', 'Score', 'اللقب']], use_container_width=True, hide_index=True)
        else:
            st.info("لا توجد بيانات لهذه المجموعة بعد.")

    with t2_2:
        if not weekly_leaderboard.empty:
            st.dataframe(weekly_leaderboard[['الترتيب', 'الاسم', 'Score']], use_container_width=True, hide_index=True)
        else:
            st.info("بداية أسبوع جديدة! شدوا الهمة.")

    with t2_3: 
        if not daily_leaderboard.empty: 
            st.dataframe(daily_leaderboard[['الترتيب', 'الاسم', 'Score']], use_container_width=True, hide_index=True)
            st.success(f"🌟 نجم اليوم: {daily_champion_name}")
        else:
            st.info("لم يسجل أحد نقاطاً اليوم.")
