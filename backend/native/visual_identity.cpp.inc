
// Footy presentation-only materials. No player attributes or animation state changes.
void HumanoidBase::ApplyVisualIdentity(const std::string& path, int skin,
                                     const std::string& hair, const std::string& colour) {
  if (!path.empty()) SetKit(GetContext().surface_manager.Fetch(path, true, true));
  if (skin >= 1 && skin <= 4) {
    auto texture = GetContext().surface_manager.Fetch(
        "media/objects/players/textures/skin0" + int_to_str(skin) + ".png", true, true);
    auto body = boost::static_pointer_cast<Geometry>(fullbodyNode->GetObject("fullbody"));
    auto& meshes = body->GetGeometryData()->GetResource()->GetTriangleMeshesRef();
    for (auto& mesh : meshes) {
      if (mesh.material.diffuseTexture && mesh.material.diffuseTexture->GetIdentString().find("skin") != std::string::npos)
        mesh.material.diffuseTexture = texture;
    }
    body->OnUpdateGeometryData();
  }
  if (!hair.empty()) {
    hairStyle->SetGeometryData(GetContext().geometry_manager.Fetch(
        "media/objects/players/hairstyles/" + hair + ".ase", true, true));
    auto texture = GetContext().surface_manager.Fetch(
        "media/objects/players/textures/hair/" + colour + ".png", true, true);
    auto& meshes = hairStyle->GetGeometryData()->GetResource()->GetTriangleMeshesRef();
    for (auto& mesh : meshes) if (mesh.material.diffuseTexture) mesh.material.diffuseTexture = texture;
    hairStyle->OnUpdateGeometryData();
  }
}

// Isolated preview only: applies joint rotations after normal render preparation.
// It does not register animations or change currentAnim, spatialState or ball data.
void HumanoidBase::ApplyPresentationClip(const std::string& path, int frame) {
  static std::map<std::string, boost::shared_ptr<Animation> > clips;
  if (!clips.count(path)) {
    boost::shared_ptr<Animation> clip(new Animation());
    clip->Load(path);
    clips[path] = clip;
  }
  auto clip = clips[path];
  frame = std::max(0, std::min(frame, clip->GetFrameCount() - 1));
  const char* parts[] = {"body", "middle", "neck", "left_shoulder", "left_elbow",
      "right_shoulder", "right_elbow", "left_thigh", "left_knee", "left_ankle",
      "right_thigh", "right_knee", "right_ankle"};
  for (const auto name : parts) {
    auto part = BodyPartFromString(name);
    Quaternion rotation;
    Vector3 translation;
    if (clip->GetKeyFrame(part, frame, rotation, translation)) nodeMap[part]->SetRotation(rotation, false);
  }
  humanoidNode->RecursiveUpdateSpatialData(e_SpatialDataType_Both);
  UpdateFullbodyNodes(false);
}
