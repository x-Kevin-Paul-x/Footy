  void visual_player_python(int team, int index, const std::string& kit,
                            int skin, const std::string& hair, const std::string& colour, const std::string& name) {
    ContextHolder c(this);
    if (team < 0 || team > 1 || index < 0 || index > 10) throw std::out_of_range("visual player");
    GetTracker()->setDisabled(true);
    context->gameTask->GetMatch()->GetTeam(team)->GetAllPlayers().at(index)->CastHumanoid()->ApplyVisualIdentity(kit, skin, hair, colour);
    auto player = context->gameTask->GetMatch()->GetTeam(team)->GetAllPlayers().at(index);
    const_cast<PlayerData*>(player->GetPlayerData())->SetPresentationName(name);
    GetTracker()->setDisabled(false);
  }

  void camera_python(int preset, int team, int index, float blend) {
    ContextHolder c(this);
    if (preset < 1 || preset > 4 || blend < 0 || blend > 1) throw std::out_of_range("presentation camera");
    GetTracker()->setDisabled(true);
    auto match = context->gameTask->GetMatch();
    match->UpdateIngameCamera(preset, team, index, blend);
    match->FetchPutBuffers();
    GetTracker()->setDisabled(false);
  }

  int validate_animation_python(const std::string& path) {
    ContextHolder c(this);
    blunted::Animation clip;
    clip.Load(path);
    return clip.GetFrameCount();
  }

  PyObject* render_clip_python(int team, int index, const std::string& path, int frame) {
    ContextHolder c(this);
    if (team < 0 || team > 1 || index < 0 || index > 10) throw std::out_of_range("presentation clip player");
    GetTracker()->setDisabled(true);
    context->gameTask->PrepareRender();
    auto player = context->gameTask->GetMatch()->GetTeam(team)->GetAllPlayers().at(index);
    player->CastHumanoid()->ApplyPresentationClip(path, frame);
    player->UpdateFullbodyModel();
    boost::static_pointer_cast<blunted::Geometry>(player->GetFullbodyNode()->GetObject("fullbody"))->OnUpdateGeometryData();
    context->graphicsSystem.GetTask()->Render(true);
    GetTracker()->setDisabled(false);
    return get_frame_python();
  }
